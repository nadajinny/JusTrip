from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import re
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

app = FastAPI()

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_KEY")

if not all([GOOGLE_API_KEY, WEATHER_API_KEY, GEMINI_API_KEY]):
    raise EnvironmentError("Missing one or more required API keys in .env")




genai.configure(api_key=GEMINI_API_KEY)

def get_ai_recommendation(loc: str, description: str, temperature: float, lat: float, lon: float, budget_krw: float = 0.0) -> str:
    budget_usd = 0.0
    if budget_krw > 0:
        exchange_rate = 0.00073
        if exchange_rate > 0:
            budget_usd = budget_krw * exchange_rate
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
        f"For each suggestion, include: name of place, location, estimated time to travel from current location, reason, and if possible, the destination's website.\n"
        f"If applicable, please format it into a bulleted list, ensuring each item starts with the name of the place.\n"
        f"Include the cost of each suggestion in both KRW and USD."
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
    budget_krw: float = Query(0.0, description="Budget for recommendations in South Korean Won (KRW). Use 0 for any budget.")
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return "<h3>Location not found in Google Maps API.</h3>"

    weather_data = get_weather(lat, lon)

    if weather_data.get("cod") != 200:
        message = weather_data.get("message", "Unknown error")
        return f"<h3>Weather API error: {message}</h3>"

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
        humidity = weather_data["main"]["humidity"]
    except KeyError as e:
        logger.error(f"Missing weather key: {str(e)}")
        return f"<h3>Weather data incomplete: Missing key {str(e)}</h3>"

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip = clean_ai_text(ai_tip_raw)
    formatted_tip = ai_tip.replace("\n", "<br>")

    if budget_krw > 0:
        budget_display = f"{budget_krw:,.0f} KRW"
        exchange_rate = 0.00073
        if exchange_rate > 0:
            budget_usd = budget_krw * exchange_rate
            budget_display += f" (approx. ${budget_usd:,.2f} USD)"
    else:
        budget_display = "Any"

    return f"""
    <h2>Weather in {formatted_address}</h2>
    <p><b>Temperature:</b> {temperature}°C</p>
    <p><b>Description:</b> {description}</p>
    <p><b>Humidity:</b> {humidity}%</p>
    <h3>AI Recommendations (Budget: {budget_display})</h3>
    <p>{formatted_tip}</p>
    """

@app.get("/weather/text", response_class=PlainTextResponse)
def weather_text(
    loc: str = Query(...),
    budget_krw: float = Query(0.0, description="Budget for recommendations in South Korean Won (KRW). Use 0 for any budget.")
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return "Location not found."

    weather_data = get_weather(lat, lon)

    if weather_data.get("cod") != 200:
        message = weather_data.get("message", "Unknown error")
        return f"Weather API error: {message}"

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
    except KeyError as e:
        logger.error(f"Missing weather key: {str(e)}")
        return f"Weather data incomplete: Missing key {str(e)}"

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip = clean_ai_text(ai_tip_raw)

    return ai_tip

@app.get("/")
def root():
    return {"status": "Server is running"}