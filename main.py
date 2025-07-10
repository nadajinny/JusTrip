from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import re
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()


GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") 
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

EXCHANGE_RATE_KRW_TO_USD = 0.00073
SAVE_DIRECTORY = Path("saved_reports")

if not all([GOOGLE_API_KEY, WEATHER_API_KEY, GEMINI_API_KEY]):
    raise EnvironmentError("Missing one or more required API keys in .env")

genai.configure(api_key=GEMINI_API_KEY)

def group_key_value_objects(flat_list, fields_per_item=5):
    grouped = []
    for i in range(0, len(flat_list), fields_per_item):
        group = {}
        for j in range(fields_per_item):
            if i + j < len(flat_list):
                group.update(flat_list[i + j])
        grouped.append(group)
    return grouped


def get_ai_recommendation(loc: str, description: str, temperature: float, lat: float, lon: float, budget_krw: float = 0.0) -> str:
    budget_usd = 0.0
    if budget_krw > 0:
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_phrase = f"a budget of {budget_krw:,} KRW (approximately ${budget_usd:,.2f} USD)"
        else:
            budget_phrase = f"a budget of {budget_krw:,} KRW (unable to convert to USD)"
    else:
        budget_phrase = "any budget"

    # IMPORTANT: Instruct the AI to explicitly include "Location:" and "Coordinates:" or similar
    # to make parsing easier for map plotting.
    prompt = (
        f"The current weather in {loc} is {description} with a temperature of {temperature}°C.\n"
        f"I am currently at coordinates ({lat}, {lon}). "
        f"Suggest 3 fun or useful things I can do near me in {loc}. Consider the temperature, I do not want to be outside if it is too hot or too cold. "
        f"Consider {budget_phrase}. You must recommend events or places that are close to the budget provided. It does not have to be free.\n"
        f"For each suggestion, include: "
        f"**Name of Place:** [Name],\n"
        f"**Location:** [Address or general area that Google Maps can understand, e.g., '123 Main St, City, Country'],\n"
        f"**Estimated Travel Time:** [Time],\n"
        f"**Description:** [Description],\n"
        # to be replaced
        f"**Website:** google.com\n" 
        f"**Cost:** [Cost in KRW and USD, e.g., '5,000 KRW / $3.65 USD']\n"
        f"If applicable, please format it into a bulleted list, ensuring each item starts with the name of the place.\n"
    )
    try:
        model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")
        response = model.generate_content(prompt)
        if hasattr(response, 'text') and isinstance(response.text, str):
            return response.text.strip()
        else:
            return "AI response missing or not in expected format."
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        return f"AI error: {str(e)}"

def get_coordinates(location: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": GOOGLE_API_KEY}
    response = requests.get(url, params=params)
    data = response.json()
    if not data.get("results"):
        return None, None, None
    result = data["results"][0]
    loc = result["geometry"]["location"]
    formatted_address = result["formatted_address"]
    return loc["lat"], loc["lng"], formatted_address

#get the coordinates for each 
def get_coordinates_for_recommendations(recommendations: list):
    for item in recommendations:
        location_str = item.get("Location")
        if location_str:
            lat, lon, _ = get_coordinates(location_str)
            if lat is not None and lon is not None:
                item["lat"] = lat
                item["lon"] = lon
            else:
                logger.warning(f"Could not get coordinates for: {location_str}")
    return recommendations


def get_weather(lat: float, lon: float):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "en"
    }
    response = requests.get(url, params=params)
    data = response.json()
    logger.info(f"Weather API raw response: {data}")
    return data

def clean_ai_text(raw_text: str) -> str:
    cleaned_lines = []
    for line in raw_text.splitlines():
        # Remove leading bullet points and extra spaces
        cleaned_line = re.sub(r'^\s*[\*\-\+]\s*', '', line)
        cleaned_lines.append(cleaned_line)
    # Join non-empty lines with double newlines for paragraph separation in HTML later
    cleaned_text = "\n\n".join(line.rstrip() for line in cleaned_lines if line.strip() != "")
    return cleaned_text


#parse json file to format
def parse_ai_blocks_to_list(text: str) -> list:
    blocks = text.strip().split('\n\n')
    results = []
    for block in blocks:
        item = {}
        lines = block.strip().splitlines()
        if not lines:
            continue
        
        first_line_is_name = True
        if re.match(r"\*\*(.+?):\*\*\s*(.+)", lines[0]):
            first_line_is_name = False
        else:
            item["Name of Place"] = re.sub(r'^\s*[\*\-\+]\s*', '', lines[0]).strip()
            
        for line in lines:
            match = re.match(r"\*\*(.+?):\*\*\s*(.+)", line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                item[key] = value
       
        if first_line_is_name and "Name of Place" not in item and lines:
            item["Name of Place"] = re.sub(r'^\s*[\*\-\+]\s*', '', lines[0]).strip()

        if item:
            results.append(item)
    return results

# Existing JSON endpoint (unchanged)
@app.get("/weather/json", response_class=JSONResponse)
def weather_json(loc: str = Query(...), budget_krw: float = Query(0.0)):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return JSONResponse({"error": "Location not found."}, status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return JSONResponse({"error": f"Weather API error: {weather_data.get('message', 'Unknown')}"}, status_code=500)

    temperature = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]
    humidity = weather_data["main"].get("humidity")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip_clean = clean_ai_text(ai_tip_raw)
    ai_items = parse_ai_blocks_to_list(ai_tip_clean)
    ai_items_with_coords = get_coordinates_for_recommendations(ai_items) # NEW

    budget_display = "Any"
    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"

    return JSONResponse({
        "location": formatted_address,
        "coordinates": {"lat": lat, "lon": lon},
        "temperature_celsius": temperature,
        "description": description,
        "humidity": humidity,
        "budget": budget_display,
        "ai_parsed": ai_items_with_coords, # Send items with coordinates
        "ai_grouped": group_key_value_objects(ai_items)
    })

@app.get("/weather/text", response_class=PlainTextResponse)
def weather_text(loc: str = Query(...), budget_krw: float = Query(0.0)):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return PlainTextResponse("Error: Location not found.", status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return PlainTextResponse(f"Error: Weather API error: {weather_data.get('message', 'Unknown')}", status_code=500)

    temperature = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]
    humidity = weather_data["main"].get("humidity")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip_clean = clean_ai_text(ai_tip_raw)

    budget_display = "Any"
    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"

    response_text = (
        f"Weather Report for {formatted_address}\n"
        f"-----------------------------------\n"
        f"Coordinates: Lat {lat}, Lon {lon}\n"
        f"Temperature: {temperature}°C\n"
        f"Description: {description}\n"
        f"Humidity: {humidity}%\n"
        f"Budget Considered: {budget_display}\n\n"
        f"AI Recommendations:\n"
        f"---------------------\n"
        f"{ai_tip_clean}"
    )
    return PlainTextResponse(response_text)

@app.get("/weather", response_class=HTMLResponse)
def weather(
    loc: str = Query(..., example="1600 Amphitheatre Parkway, Mountain View, CA"),
    budget_krw: float = Query(0.0, description="Budget for recommendations in South Korean Won (KRW). Use 0 for any budget."),
    save_to_file: bool = Query(False, description="Set to true to save the report to a local HTML file.")
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return HTMLResponse("<h3>Location not found in Google Maps API.</h3>")

    weather_data = get_weather(lat, lon)

    if weather_data.get("cod") != 200:
        message = weather_data.get("message", "Unknown error")
        return HTMLResponse(f"<h3>Weather API error: {message}</h3>")

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
        humidity = weather_data["main"]["humidity"]
    except KeyError as e:
        logger.error(f"Missing weather key: {str(e)}")
        return HTMLResponse(f"<h3>Weather data incomplete: Missing key {str(e)}</h3>")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip = clean_ai_text(ai_tip_raw)
    formatted_tip = ai_tip.replace("\n", "<br>")

    ai_items = parse_ai_blocks_to_list(ai_tip_raw) # Use raw AI tip for parsing structure
    ai_items_with_coords = get_coordinates_for_recommendations(ai_items)

    # Prepare marker data for JavaScript
    markers_js_array = []
    for item in ai_items_with_coords:
        if "lat" in item and "lon" in item:
            name = item.get("Name of Place", "Unknown Place")
            location = item.get("Location", "Unknown Location")
            description_text = item.get("Description", "No description available.")
            travel_time = item.get("Estimated Travel Time", "N/A")
            cost = item.get("Cost", "N/A")
            website = item.get("Website", "#") # Default to '#' for website if not available

            # Create content for the info window
            info_content = (
                f"<b>{name}</b><br>"
                f"Location: {location}<br>"
                f"Travel Time: {travel_time}<br>"
                f"Cost: {cost}<br>"
                f"Description: {description_text}<br>"
            )
            # Ensure website is a valid URL before linking
            if website != "#" and website.startswith(("http://", "https://")):
                info_content += f"<a href='{website}' target='_blank'>Website</a>"
            elif website != "#" and not website.startswith(("http://", "https://")):
                 # If website is provided but missing protocol, try to prepend
                 info_content += f"<a href='https://{website}' target='_blank'>Website</a>"


            markers_js_array.append({
                "position": {"lat": item["lat"], "lng": item["lon"]},
                "title": name,
                "infoContent": info_content # HTML content for info window
            })

    # Add current location marker
    markers_js_array.append({
        "position": {"lat": lat, "lng": lon},
        "title": "Your Current Location",
        "infoContent": f"<b>You Are Here:</b><br>{formatted_address}"
    })


    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"
    else:
        budget_display = "Any"

    # Conditionally include the raw AI response section
    raw_ai_section = ""
    if save_to_file: # Only include raw AI response if saving to file
        raw_ai_section = f"""
        <h3>Raw Gemini AI Response</h3>
        <pre>{ai_tip_raw}</pre>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weather Report for {formatted_address}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }}
            h2, h3 {{ color: #0056b3; }}
            p {{ margin-bottom: 5px; }}
            b {{ color: #555; }}
            pre {{ background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            #map {{ height: 500px; width: 100%; border: 1px solid #ccc; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h2>Weather in {formatted_address}</h2>
        <p><b>Temperature:</b> {temperature}°C</p>
        <p><b>Description:</b> {description}</p>
        <p><b>Humidity:</b> {humidity}%</p>
        <h3>AI Recommendations (Budget: {budget_display})</h3>
        <p>{formatted_tip}</p>

        <h3>Recommended Locations on Map</h3>
        <div id="map"></div>

        {raw_ai_section}

        <script>
            let map;
            let markers = [];
            let infoWindows = [];

            const YOUR_LAT = {lat};
            const YOUR_LON = {lon};
            const MARKERS = {markers_js_array}; // This will inject the Python list as a JS array

            async function initMap() {{
                const mapsLib = await google.maps.importLibrary("maps");
                const markerLib = await google.maps.importLibrary("marker");
                const Map = mapsLib.Map;
                const AdvancedMarkerElement = markerLib.AdvancedMarkerElement;


                map = new Map(document.getElementById("map"), {{
                    zoom: 12,
                    center: {{ lat: YOUR_LAT, lng: YOUR_LON }},
                    mapId: "DEMO_MAP_ID", // You can create your own Map ID in Google Cloud Console
                }});

                // Add current location marker
                const currentMarker = new AdvancedMarkerElement({{
                    map: map,
                    position: {{ lat: YOUR_LAT, lng: YOUR_LON }},
                    title: "Your Current Location",
                }});
                const currentInfoWindow = new google.maps.InfoWindow({{
                    content: "<b>You Are Here:</b><br>{formatted_address}",
                }});
                currentMarker.addListener("click", () => {{
                    currentInfoWindow.open(map, currentMarker);
                }});
                markers.push(currentMarker);
                infoWindows.push(currentInfoWindow);


                // Add markers for recommendations
                MARKERS.forEach((data, index) => {{
                    // The last marker in MARKERS is the current location, skip it for recommendations loop
                    if (index === MARKERS.length - 1 && data.title === "Your Current Location") return; 
                    
                    const marker = new AdvancedMarkerElement({{
                        map: map,
                        position: data.position,
                        title: data.title,
                    }});

                    const infoWindow = new google.maps.InfoWindow({{
                        content: data.infoContent,
                    }});

                    marker.addListener("click", () => {{
                        infoWindows.forEach(iw => iw.close()); // Close all other info windows
                        infoWindow.open(map, marker);
                    }});

                    markers.push(marker);
                    infoWindows.push(infoWindow);
                }});

                // Adjust map bounds to fit all markers
                if (markers.length > 0) {{
                    const bounds = new google.maps.LatLngBounds();
                    markers.forEach(marker => bounds.extend(marker.position));
                    map.fitBounds(bounds);
                }}
            }}

            // Load Google Maps API script
            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key={GOOGLE_API_KEY}&callback=initMap&v=beta&libraries=marker`;
            script.async = true;
            document.head.appendChild(script);
        </script>
    </body>
    </html>
    """
    
    # This is the corrected and consolidated save_to_file logic
    if save_to_file:
        SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_loc_name = re.sub(r'[^\w\s-]', '', formatted_address).strip().replace(' ', '_')[:50]
        filename = SAVE_DIRECTORY / f"weather_report_full_{safe_loc_name}_{timestamp}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            return PlainTextResponse(f"Combined HTML weather report and AI suggestions saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving HTML file: {e}")
            return PlainTextResponse(f"Error saving HTML file: {e}", status_code=500)
    else:
        return HTMLResponse(content=html_content)


@app.get("/")
def root():
    return {"status": "Server is running"}