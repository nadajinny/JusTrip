from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
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

# Define the exchange rate as a global variable
EXCHANGE_RATE_KRW_TO_USD = 0.00073

# Define the directory for saving reports
SAVE_DIRECTORY = Path("saved_reports")

if not all([GOOGLE_API_KEY, WEATHER_API_KEY, GEMINI_API_KEY]):
    raise EnvironmentError("Missing one or more required API keys in .env")


genai.configure(api_key=GEMINI_API_KEY)

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

    prompt = (
        f"The current weather in {loc} is {description} with a temperature of {temperature}°C.\n"
        f"I am currently at coordinates ({lat}, {lon}). "
        f"Suggest 3 fun or useful things I can do near me in {loc}. "
        f"Consider {budget_phrase}.\n"
        f"For each suggestion, include: name of place, location, estimated time to travel from current location, description, and if possible, the destination's website.\n"
        f"If applicable, please format it into a bulleted list, ensuring each item starts with the name of the place.\n"
        f"Include the cost of each suggestion in both KRW and USD. This should be in one "
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
        cleaned_line = re.sub(r'^\s*\*\s*', '', line)
        cleaned_lines.append(cleaned_line)
    cleaned_text = "\n\n".join(line.rstrip() for line in cleaned_lines if line.strip() != "")
    return cleaned_text

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
        </style>
    </head>
    <body>
        <h2>Weather in {formatted_address}</h2>
        <p><b>Temperature:</b> {temperature}°C</p>
        <p><b>Description:</b> {description}</p>
        <p><b>Humidity:</b> {humidity}%</p>
        <h3>AI Recommendations (Budget: {budget_display})</h3>
        <p>{formatted_tip}</p>
        {raw_ai_section}
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

@app.get("/weather/text", response_class=PlainTextResponse)
def weather_text(
    loc: str = Query(...),
    budget_krw: float = Query(0.0, description="Budget for recommendations in South Korean Won (KRW). Use 0 for any budget."),
    save_to_file: bool = Query(False, description="Set to true to save the report to a local plain text file."),
    save_ai_raw_text: bool = Query(False, description="Set to true to save the raw AI response text to a file.")
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return PlainTextResponse("Location not found.")

    weather_data = get_weather(lat, lon)

    if weather_data.get("cod") != 200:
        message = weather_data.get("message", "Unknown error")
        return PlainTextResponse(f"Weather API error: {message}")

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
    except KeyError as e:
        logger.error(f"Missing weather key: {str(e)}")
        return PlainTextResponse(f"Weather data incomplete: Missing key {str(e)}")

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip = clean_ai_text(ai_tip_raw)

    # Re-calculating budget_display for the plain text response for consistency
    budget_display = "Any"
    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        if EXCHANGE_RATE_KRW_TO_USD > 0:
            budget_usd = budget_krw * EXCHANGE_RATE_KRW_TO_USD
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"

    text_content = f"""Weather in {formatted_address}
Temperature: {temperature}°C
Description: {description}
Humidity: {weather_data["main"]["humidity"]}%

AI Recommendations (Budget: {budget_display})
{ai_tip}
"""
    
    response_messages = []

    if save_to_file:
        SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_loc_name = re.sub(r'[^\w\s-]', '', formatted_address).strip().replace(' ', '_')[:50]
        filename = SAVE_DIRECTORY / f"weather_report_{safe_loc_name}_{timestamp}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text_content)
            response_messages.append(f"Plain text weather report saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving plain text file: {e}")
            response_messages.append(f"Error saving plain text file: {e}")

    if save_ai_raw_text:
        SAVE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_loc_name = re.sub(r'[^\w\s-]', '', formatted_address).strip().replace(' ', '_')[:50]
        ai_filename = SAVE_DIRECTORY / f"ai_raw_suggestions_{safe_loc_name}_{timestamp}.txt"
        try:
            with open(ai_filename, "w", encoding="utf-8") as f:
                f.write(ai_tip_raw)
            response_messages.append(f"Raw AI suggestions saved to {ai_filename}")
        except Exception as e:
            logger.error(f"Error saving raw AI text file: {e}")
            response_messages.append(f"Error saving raw AI text file: {e}")

    if response_messages:
        return PlainTextResponse("\n".join(response_messages))
    else:
        return PlainTextResponse(content=text_content)

@app.get("/")
def root():
    return {"status": "Server is running"}
