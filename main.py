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
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

EXCHANGE_RATE_KRW_TO_USD = 0.00073
SAVE_DIRECTORY = Path("saved_reports")

URL_PROTOCOL_REGEX = re.compile(r'^(http|https)://', re.IGNORECASE)

if not all([GOOGLE_API_KEY, WEATHER_API_KEY, GEMINI_API_KEY]):
    raise EnvironmentError("Missing one or more required API keys in .env")

genai.configure(api_key=GEMINI_API_KEY)

def html_escape(text):
    if text is None:
        return ''
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

def get_ai_recommendation(loc: str, description: str, temperature: float, lat: float, lon: float, budget_krw: float = 0.0, interests: list[str] = []) -> str:
    budget_usd = 0.0
    if budget_krw > 0:
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_phrase = f"a budget of {budget_krw:,} KRW (approximately ${budget_usd:,.2f} USD)"
        else:
            budget_phrase = f"a budget of {budget_krw:,} KRW (unable to convert to USD)"
    else:
        budget_phrase = "any budget"

    interests_phrase = ""
    if interests:
        interests_str = ", ".join(interests)
        interests_phrase = f"Also, consider my interests in: {interests_str}. "

    prompt = (
        f"The current weather in {loc} is {description} with a temperature of {temperature}°C.\n"
        f"I am currently at coordinates ({lat}, {lon}). "
        f"Suggest 3 fun or useful things I can do near me in {loc}. Consider the temperature, I do not want to be outside if it is too hot or too cold. "
        f"Consider {budget_phrase}. {interests_phrase}"
        f"You must recommend events or places that are close to the budget provided. It does not have to be free.\n"
        f"Format your response as a JSON array of objects, where each object represents a recommendation.\n"
        f"Each object should have the following keys:\n"
        f"- `name`: (string) The name of the place or event.\n"
        f"- `location`: (string) The address or a general area that Google Maps can understand (e.g., '123 Main St, City, Country'). If unknown, use 'N/A'.\n"
        f"- `travel_time`: (string) Estimated travel time (e.g., '5-10 minutes walk', '20 minutes by bus'). If unknown, use 'N/A'.\n"
        f"- `description`: (string) A detailed description.\n"
        f"- `website`: (string) The official website URL (e.g., '[https://example.com](https://example.com)'). If no website, use 'N/A'.\n"
        f"- `cost_krw`: (number) Estimated cost in KRW. Use 0 for free. If unknown, use 0.\n"
        f"- `cost_usd`: (number) Estimated cost in USD. Use 0 for free. If unknown, use 0.\n"
        f"- `recommended_clothing`: (string) Specific clothing recommendation for this location/activity based on weather (e.g., 'Light t-shirt and shorts', 'Warm jacket and gloves').\n"
        f"- `recommended_essentials`: (string) Specific essential items for this location/activity (e.g., 'sunscreen, hat, water bottle', 'umbrella, comfortable walking shoes').\n"
        f"Ensure the cost fields are numeric. If the cost is a range, provide a reasonable average or the lower end.\n"
        f"Example JSON structure:\n"
        f"```json\n"
        f"[\n"
        f"  {{\n"
        f'    "name": "Gwangju National Museum",\n'
        f'    "location": "110 Hanam-daero, Buk-gu, Gwangju, South Korea",\n'
        f'    "travel_time": "20 minutes by bus",\n'
        f'    "description": "Explore historical artifacts and cultural exhibits.",\n'
        f'    "website": "[https://gwangju.museum.go.kr](https://gwangju.museum.go.kr)",\n'
        f'    "cost_krw": 0,\n'
        f'    "cost_usd": 0,\n'
        f'    "recommended_clothing": "Casual clothes, comfortable walking shoes",\n'
        f'    "recommended_essentials": "Water bottle, camera"\n'
        f"  }}\n"
        f"]\n"
        f"```\n"
        f"Provide only the JSON. Do not include any conversational text outside the JSON block.\n"
    )
    try:
        model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        if hasattr(response, 'text') and isinstance(response.text, str):
            json_match = re.search(r'```json\s*(.*?)\s*```', response.text.strip(), re.DOTALL)
            if json_match:
                return json_match.group(1).strip()
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


def get_coordinates_for_recommendations(recommendations: list):
    for item in recommendations:
        location_str = item.get("Location")
        if location_str and location_str != "N/A":
            lat, lon, _ = get_coordinates(location_str)
            if lat is not None and lon is not None:
                item["lat"] = lat
                item["lon"] = lon
            else:
                logger.warning(f"Could not get coordinates for: {location_str}")
    return recommendations


def parse_ai_response(json_string: str) -> list:
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', json_string, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            json_content = json_string

        parsed_data = json.loads(json_content)
        if not isinstance(parsed_data, list):
            logger.warning(f"AI response is not a JSON list: {parsed_data}. Attempting to wrap.")
            if isinstance(parsed_data, dict):
                parsed_data = [parsed_data]
            else:
                return []

        standardized_items = []
        for item in parsed_data:
            standardized_item = {
                "Name of Place": item.get("name", "N/A"),
                "Location": item.get("location", "N/A"),
                "Estimated Travel Time": item.get("travel_time", "N/A"),
                "Description": item.get("description", "N/A"),
                "Website": item.get("website", "N/A"),
                "Cost_KRW": item.get("cost_krw", 0.0),
                "Cost_USD": item.get("cost_usd", 0.0),
                "Recommended_Clothing": item.get("recommended_clothing", "N/A"),
                "Recommended_Essentials": item.get("recommended_essentials", "N/A"),
                "lat": None,
                "lon": None
            }
            if standardized_item["Website"] != "N/A" and standardized_item["Website"].strip():
                if not URL_PROTOCOL_REGEX.match(standardized_item["Website"]):
                    standardized_item["Website"] = "https://" + standardized_item["Website"]
            standardized_items.append(standardized_item)

        return standardized_items
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from AI response: {e}. Raw response: {json_string}")
        cleaned_json_string = re.sub(r',\s*}', '}', json_string)
        cleaned_json_string = re.sub(r',\s*]', ']', cleaned_json_string)
        cleaned_json_string = re.sub(r'//.*?\n|/\*.*?\*/', '', cleaned_json_string, flags=re.DOTALL)
        try:
            parsed_data = json.loads(cleaned_json_string)
            if not isinstance(parsed_data, list):
                if isinstance(parsed_data, dict):
                    parsed_data = [parsed_data]
                else:
                    return []
            standardized_items = []
            for item in parsed_data:
                standardized_item = {
                    "Name of Place": item.get("name", "N/A"),
                    "Location": item.get("location", "N/A"),
                    "Estimated Travel Time": item.get("travel_time", "N/A"),
                    "Description": item.get("description", "N/A"),
                    "Website": item.get("website", "N/A"),
                    "Cost_KRW": item.get("cost_krw", 0.0),
                    "Cost_USD": item.get("cost_usd", 0.0),
                    "Recommended_Clothing": item.get("recommended_clothing", "N/A"),
                    "Recommended_Essentials": item.get("recommended_essentials", "N/A"),
                    "lat": None,
                    "lon": None
                }
                if standardized_item["Website"] != "N/A" and standardized_item["Website"].strip():
                    if not URL_PROTOCOL_REGEX.match(standardized_item["Website"]):
                        standardized_item["Website"] = "https://" + standardized_item["Website"]
                standardized_items.append(standardized_item)
            return standardized_items
        except json.JSONDecodeError as e_retry:
            logger.error(f"Failed to decode JSON even after cleaning: {e_retry}. Cleaned response: {cleaned_json_string}")
            return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during JSON parsing: {e}. Raw response: {json_string}")
        return []


@app.get("/weather/json", response_class=JSONResponse)
def weather_json(loc: str = Query(...), budget_krw: float = Query(0.0), interests: list[str] = Query([])):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return JSONResponse({"error": "Location not found."}, status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return JSONResponse({"error": f"Weather API error: {weather_data.get('message', 'Unknown')}"}, status_code=500)

    temperature = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]
    humidity = weather_data["main"].get("humidity")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw, interests)
    ai_items = parse_ai_response(ai_tip_raw)
    ai_items_with_coords = get_coordinates_for_recommendations(ai_items)

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
        "interests": interests,
        "ai_recommendations": ai_items_with_coords
    })


@app.get("/weather/text", response_class=PlainTextResponse)
def weather_text(loc: str = Query(...), budget_krw: float = Query(0.0), interests: list[str] = Query([])):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return PlainTextResponse("Error: Location not found.", status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return PlainTextResponse(f"Error: Weather API error: {weather_data.get('message', 'Unknown')}", status_code=500)

    temperature = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]
    humidity = weather_data["main"].get("humidity")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw, interests)
    ai_items = parse_ai_response(ai_tip_raw)

    budget_display = "Any"
    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"

    interests_display = ", ".join(interests) if interests else "None"

    recommendations_text = ""
    for item in ai_items:
        cost_display = ""
        cost_krw_val = item.get("Cost_KRW", 0.0)
        cost_usd_val = item.get("Cost_USD", 0.0)
        if cost_krw_val > 0:
            cost_display += f"{cost_krw_val:,.0f} KRW"
        if cost_usd_val > 0:
            if cost_display:
                cost_display += " / "
            cost_display += f"${cost_usd_val:,.2f} USD"
        if not cost_display and cost_krw_val == 0 and cost_usd_val == 0:
             cost_display = "Free"
        if not cost_display:
            cost_display = "N/A"

        recommendations_text += (
            f"  - Name: {item.get('Name of Place', 'N/A')}\n"
            f"    Location: {item.get('Location', 'N/A')}\n"
            f"    Travel Time: {item.get('Estimated Travel Time', 'N/A')}\n"
            f"    Description: {item.get('Description', 'N/A')}\n"
            f"    Website: {item.get('Website', 'N/A')}\n"
            f"    Cost: {cost_display}\n"
            f"    Recommended Clothing: {item.get('Recommended_Clothing', 'N/A')}\n"
            f"    Recommended Essentials: {item.get('Recommended_Essentials', 'N/A')}\n\n"
        )

    response_text = (
        f"Weather Report for {formatted_address}\n"
        f"-----------------------------------\n"
        f"Coordinates: Lat {lat}, Lon {lon}\n"
        f"Temperature: {temperature}°C\n"
        f"Description: {description}\n"
        f"Humidity: {humidity}%\n"
        f"Budget Considered: {budget_display}\n"
        f"Interests: {interests_display}\n\n"
        f"AI Recommendations:\n"
        f"-------------------------------\n"
        f"{recommendations_text}"
    )
    return PlainTextResponse(response_text)


@app.get("/weather", response_class=HTMLResponse)
def weather(
    loc: str = Query(..., example="1600 Amphitheatre Parkway, Mountain View, CA"),
    budget_krw: float = Query(0.0, description="Budget for recommendations in South Korean Won (KRW). Use 0 for any budget."),
    interests: list[str] = Query([], description="A comma-separated list of interests (e.g., 'museums,food,parks')."),
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

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw, interests)
    ai_items = parse_ai_response(ai_tip_raw)
    ai_items_with_coords = get_coordinates_for_recommendations(ai_items)

    markers_js_array = []
    for item in ai_items_with_coords:
        if "lat" in item and "lon" in item:
            name = item.get("Name of Place", "Unknown Place")
            location = item.get("Location", "Unknown Location")
            description_text = item.get("Description", "No description available.")
            travel_time = item.get("Estimated Travel Time", "N/A")
            recommended_clothing = item.get("Recommended_Clothing", "N/A")
            recommended_essentials = item.get("Recommended_Essentials", "N/A")

            cost_krw_val = item.get("Cost_KRW", 0.0)
            cost_usd_val = item.get("Cost_USD", 0.0)
            cost_display = "N/A"

            cost_parts = []
            if cost_krw_val > 0:
                cost_parts.append(f"{cost_krw_val:,.0f} KRW")
            if cost_usd_val > 0:
                cost_parts.append(f"${cost_usd_val:,.2f} USD")
            cost_display = " / ".join(cost_parts) if cost_parts else "N/A"
            if cost_krw_val == 0 and cost_usd_val == 0 and ("free" in str(item.get('description', '')).lower() or "free" in str(item.get('name', '')).lower()):
                cost_display = "Free"


            website = item.get("Website", "N/A")

            escaped_name = html_escape(name)
            escaped_location = html_escape(location)
            escaped_description_text = html_escape(description_text)
            escaped_travel_time = html_escape(travel_time)
            escaped_cost_display = html_escape(cost_display)
            escaped_recommended_clothing = html_escape(recommended_clothing)
            escaped_recommended_essentials = html_escape(recommended_essentials)

            info_content = (
                f"<b>{escaped_name}</b><br>"
                f"Location: {escaped_location}<br>"
                f"Travel Time: {escaped_travel_time}<br>"
                f"Cost: {escaped_cost_display}<br>"
                f"Description: {escaped_description_text}<br>"
                f"Clothing: {escaped_recommended_clothing}<br>"
                f"Essentials: {escaped_recommended_essentials}<br>"
            )

            if website and website != "N/A" and website.strip():
                info_content += f"<a href='{html_escape(website)}' target='_blank'>Website</a>"
            else:
                info_content += "Website: N/A"


            markers_js_array.append({
                "position": {"lat": item["lat"], "lng": item["lon"]},
                "title": name,
                "infoContent": info_content
            })


    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"
    else:
        budget_display = "Any"

    interests_display = ", ".join(interests) if interests else "None"

    raw_ai_section = ""
    if save_to_file:
        raw_ai_section = f"""
        <h3>Raw Gemini AI Response (JSON)</h3>
        <pre>{html_escape(ai_tip_raw)}</pre>
        """

    my_location_marker_color = "blue"

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
            ul {{ list-style-type: disc; margin-left: 20px; }}
            li {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <h2>Weather in {formatted_address}</h2>
        <p><b>Temperature:</b> {temperature}°C</p>
        <p><b>Description:</b> {description}</p>
        <p><b>Humidity:</b> {humidity}%</p>
        <p><b>Interests:</b> {interests_display}</p>

        <h3>AI Recommendations (Budget: {budget_display})</h3>
        <ul>
            {''.join([
                f"""
                <li>
                    <b>{html_escape(item.get('Name of Place', 'N/A'))}</b><br>
                    Location: {html_escape(item.get('Location', 'N/A'))}<br>
                    Travel Time: {html_escape(item.get('Estimated Travel Time', 'N/A'))}<br>
                    Description: {html_escape(item.get('Description', 'N/A'))}<br>
                    Website: {f'<a href="{html_escape(item["Website"])}" target="_blank">{html_escape(item["Website"])}</a>' if item.get('Website') != 'N/A' else 'N/A'}<br>
                    Cost: {f"{item.get('Cost_KRW', 0.0):,.0f} KRW" + (f" / ${item.get('Cost_USD', 0.0):,.2f} USD" if item.get('Cost_USD', 0.0) > 0 else '') if item.get('Cost_KRW', 0.0) > 0 or item.get('Cost_USD', 0.0) > 0 else ('Free' if item.get('Cost_KRW', 0.0) == 0 and item.get('Cost_USD', 0.0) == 0 else 'N/A')}<br>
                    <b>Recommended Clothing:</b> {html_escape(item.get('Recommended_Clothing', 'N/A'))}<br>
                    <b>Recommended Essentials:</b> {html_escape(item.get('Recommended_Essentials', 'N/A'))}
                </li>
                """
                for item in ai_items_with_coords
            ])}
        </ul>
        {raw_ai_section}


        <h3>Recommended Locations on Map</h3>
        <div id="map"></div>


        <script>
            let map;
            let markers = [];
            let infoWindows = [];

            const YOUR_LAT = {lat};
            const YOUR_LON = {lon};
            const MARKERS = {json.dumps(markers_js_array)};
            const MY_LOCATION_MARKER_COLOR = "{my_location_marker_color}";

            async function initMap() {{
                const mapsLib = await google.maps.importLibrary("maps");
                const markerLib = await google.maps.importLibrary("marker");
                const Map = mapsLib.Map;
                const AdvancedMarkerElement = markerLib.AdvancedMarkerElement;


                map = new Map(document.getElementById("map"), {{
                    zoom: 12,
                    center: {{ lat: YOUR_LAT, lng: YOUR_LON }},
                    mapId: "DEMO_MAP_ID",
                }});

                const svgIcon = document.createElement('div');
                svgIcon.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="` + MY_LOCATION_MARKER_COLOR + `" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5S10.62 6.5 12 6.5s2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                    </svg>
                `;

                const currentMarker = new AdvancedMarkerElement({{
                    map: map,
                    position: {{ lat: YOUR_LAT, lng: YOUR_LON }},
                    title: "Your Current Location",
                    content: svgIcon
                }});
                const currentInfoWindow = new google.maps.InfoWindow({{
                    content: "<b>You Are Here:</b><br>{html_escape(formatted_address)}",
                }});
                currentMarker.addListener("click", () => {{
                    currentInfoWindow.open(map, currentMarker);
                }});
                markers.push(currentMarker);
                infoWindows.push(currentInfoWindow);


                MARKERS.forEach((data, index) => {{
                    const marker = new AdvancedMarkerElement({{
                        map: map,
                        position: data.position,
                        title: data.title,
                    }});

                    const infoWindow = new google.maps.InfoWindow({{
                        content: data.infoContent,
                    }});

                    marker.addListener("click", () => {{
                        infoWindows.forEach(iw => iw.close());
                        infoWindow.open(map, marker);
                    }});

                    markers.push(marker);
                    infoWindows.push(infoWindow);
                }});

                if (markers.length > 0) {{
                    const bounds = new google.maps.LatLngBounds();
                    markers.forEach(marker => bounds.extend(marker.position));
                    map.fitBounds(bounds);
                }}
            }}

            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key={GOOGLE_API_KEY}&callback=initMap&v=beta&libraries=marker`;
            script.async = true;
            document.head.appendChild(script);
        </script>
    </body>
    </html>
    """

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