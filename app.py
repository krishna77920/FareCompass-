import sys
import math
import requests
import argparse
import webbrowser
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import csv
import io
import re


# small helpers
def fetch_json(url, **kwargs):
    # so we don't write try/except 20 times
    try:
        res = requests.get(url, timeout=10, **kwargs)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print("request failed:", e)
        return None


def clean_filename(text):
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip())
    return text.strip("_") or "location"

# location + distance


def geocode(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json", "limit": 1}
    headers = {"User-Agent": "farecompass"}

    data = fetch_json(url, params=params, headers=headers)
    if data and isinstance(data, list):
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def get_distance(origin, dest):
    src = geocode(origin)
    dst = geocode(dest)

    if not src or not dst:
        return None

    # try OSRM first
    url = f"http://router.project-osrm.org/route/v1/driving/{src[1]},{src[0]};{dst[1]},{dst[0]}?overview=false"
    data = fetch_json(url)

    if data and data.get("code") == "Ok":
        route = data["routes"][0]
        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60, 1),
            "src": src,
            "dst": dst,
        }

    # fallback (rough but works)
    print("OSRM failed, using rough estimate...")

    lat1, lon1 = map(math.radians, src)
    lat2, lon2 = map(math.radians, dst)

    dlat, dlon = lat2 - lat1, lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    dist = 6371 * 2 * math.asin(math.sqrt(a))

    dist *= 1.3  # roads aren't straight

    return {
        "distance_km": round(dist, 2),
        "duration_min": round(dist / 30 * 60, 1),
        "src": src,
        "dst": dst,
    }

# fare logic

def build_fares(app, color, vehicles, dist, time):
    results = []

    for v in vehicles:
        base = v["base"] + v["per_km"] * dist + v["per_min"] * time

        low = base * v.get("surge_min", 1)
        high = base * v.get("surge_max", 1)

        results.append({
            "platform": app,
            "vehicle": v["name"],
            "icon": v["icon"],
            "fare_low": round(low),
            "fare_high": round(high),
            "fare_display": f"₹{round(low)} - ₹{round(high)}",
            "eta": f"{v['eta_min']}–{v['eta_max']} min",
            "capacity": v["capacity"],
            "color": color,
        })

    return results


def ola_fares(dist, time):
    return build_fares("Ola", "#F97316", [
        {"name": "Mini", "base": 49, "per_km": 11, "per_min": 1, "surge_max": 2.5, "icon": "🚗", "eta_min": 3, "eta_max": 8, "capacity": 4},
        {"name": "Sedan", "base": 79, "per_km": 14, "per_min": 1.5, "surge_max": 2.0, "icon": "🚘", "eta_min": 5, "eta_max": 12, "capacity": 4},
        {"name": "Auto", "base": 30, "per_km": 8, "per_min": 0.5, "surge_max": 1.5, "icon": "🛺", "eta_min": 2, "eta_max": 6, "capacity": 4},
    ], dist, time)


def uber_fares(dist, time):
    return build_fares("Uber", "#000000", [
        {"name": "Go", "base": 50, "per_km": 10, "per_min": 1.2, "surge_max": 2.8, "icon": "🚗", "eta_min": 3, "eta_max": 9, "capacity": 4},
        {"name": "Premier", "base": 75, "per_km": 14.5, "per_min": 1.7, "surge_max": 2.2, "icon": "🚘", "eta_min": 5, "eta_max": 13, "capacity": 4},
        {"name": "Moto", "base": 20, "per_km": 5, "per_min": 0.5, "surge_max": 1.3, "icon": "🏍️", "eta_min": 2, "eta_max": 5, "capacity": 1},
    ], dist, time)


def rapido_fares(dist, time):
    return build_fares("Rapido", "#FACC15", [
        {"name": "Bike", "base": 20, "per_km": 4.5, "per_min": 0.4, "surge_max": 1.5, "icon": "🏍️", "eta_min": 1, "eta_max": 5, "capacity": 1},
        {"name": "Auto", "base": 28, "per_km": 7, "per_min": 0.6, "surge_max": 1.4, "icon": "🛺", "eta_min": 2, "eta_max": 6, "capacity": 3},
    ], dist, time)


def redbus_fares(dist):
    buses = [
        {"name": "Ordinary", "per_km": 0.65, "min": 12},
        {"name": "AC", "per_km": 1.8, "min": 150},
    ]

    res = []
    for b in buses:
        fare = max(b["min"], b["per_km"] * dist)
        res.append({
            "platform": "RedBus",
            "vehicle": b["name"],
            "icon": "🚌",
            "fare_low": round(fare * 0.9),
            "fare_high": round(fare * 1.2),
            "fare_display": f"₹{round(fare*0.9)} - ₹{round(fare*1.2)}",
            "eta": "depends",
            "capacity": 40,
            "color": "#EF4444",
        })
    return res


# main logic

def compare_all(origin, dest):
    print(f"\nchecking: {origin} -> {dest}")

    route = get_distance(origin, dest)
    if not route:
        return {"error": "couldn't find that route"}

    dist = route["distance_km"]
    time = route["duration_min"]

    fares = []
    fares += ola_fares(dist, time)
    fares += uber_fares(dist, time)
    fares += rapido_fares(dist, time)
    fares += redbus_fares(dist)

    fares.sort(key=lambda x: x["fare_low"])

    return {
        "from": origin,
        "to": dest,
        "distance": dist,
        "time": time,
        "fares": fares,
        "best": fares[0] if fares else None,
        "timestamp": datetime.now().strftime("%H:%M"),
    }

app = Flask(__name__)
cache = {}

@app.route("/")
def home():
    return "<h2>FareCompass running 🚕</h2>"

@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    origin = data.get("origin", "")
    dest = data.get("destination", "")

    result = compare_all(origin, dest)
    global cache
    cache = result

    return jsonify(result)


@app.route("/download")
def download():
    if not cache:
        return "no data"

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Platform", "Vehicle", "Low", "High"])

    for f in cache["fares"]:
        writer.writerow([f["platform"], f["vehicle"], f["fare_low"], f["fare_high"]])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="fares.csv"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to", dest="end")
    parser.add_argument("--port", type=int, default=5050)

    args = parser.parse_args()

    start = args.start or input("start location: ")
    end = args.end or input("destination: ")

    if not start or not end:
        print("both locations needed 😅")
        return

    result = compare_all(start, end)

    if "error" in result:
        print(result["error"])
        return

    best = result["best"]
    print(f"\nbest option: {best['vehicle']} on {best['platform']} → {best['fare_display']}")

    print(f"\nstarting server at http://localhost:{args.port}")
    threading.Timer(1, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()

    app.run(port=args.port)


if __name__ == "__main__":
    main()
