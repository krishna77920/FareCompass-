FareCompass

I created a small tool to answer one question: 

“What’s the cheapest way to get from A to B right now?”

Instead of checking 3 or 4 apps and making guesses, this tool lets you compare ride services all in one place.

What it does: 

You provide a starting point and a destination.

It:

- figures out the distance using maps APIs
- estimates the travel time
- calculates fare ranges for different platforms
- shows you the cheapest option

No logins, no API keys, no fuss.

Features 
Compare fares from: 
- Ola 
- Uber 
- Rapido 
- RedBus 
It shows the fare range from low to high because surge pricing happens.  
It also provides the estimated time of arrival, vehicle type, and capacity.  
Results are sorted so the cheapest option appears first.  
It has a simple Flask API that you can connect to anything.  
You can download results as CSV files because it’s useful.  

How it works (simple version) 
It converts your locations into coordinates using OpenStreetMap.  
It tries to get the actual route distance via OSRM.  
If that fails, it uses a rough estimate.  
It runs fare calculations for each platform.  
Then, it sorts everything by the cheapest option.

That’s it. No magic, just math and APIs.

Tech stack:
- Python 
- Flask 
- Requests 
- OpenStreetMap (Nominatim) 
- OSRM (routing) 
- Some basic math (nothing complicated)

Setup (step-by-step) 
1. Clone the repo  
   git clone https://github.com/yourusername/farecompass.git  
   cd farecompass  
2. Install the dependencies  
   pip install flask requests  
3. Run it  
   python app.py --from "Indore" --to "Bhopal"  
   Or simply:  
   python app.py  
   …and it’ll ask you for the locations.

4. It’ll automatically open: http://localhost:5050  

You can access the API: POST /search  

Example body:

{
  "origin": "Indore",
  "destination": "Bhopal"
}  
5. Download results  

After running a search: 

GET /download  

You’ll receive a CSV file with fares.  

Example output:  
best option: Bike on Rapido → ₹120 - ₹160  

You’ll also see all options sorted by price.  

Limitations:  
These are estimates, not real-time prices.  
Surge pricing is a guess, not live data.  
It relies on free APIs, so it can sometimes fail.  
Location searches aren’t perfect, especially for small places.  
There’s no traffic or peak hour logic yet.  
RedBus is very rough, basically educated guessing.  

So please don’t blame this tool if your ride ends up costing more.

Future ideas:  
Here are some features I’d add if I continue working on this:  
- Real API integrations if I ever get access  
- A more modern UI  
- Save and search history  
- Better surge predictions  
- More services (BluSmart, Metro, etc.)  
- A mobile-friendly version  
- Maybe even a Chrome extension.
