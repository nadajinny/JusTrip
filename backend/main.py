from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
import os
import requests
from dotenv import load_dotenv
import google.generativeai as genai
import re
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

app = FastAPI()

# 📌 정적 파일(css, js) 제공
app.mount("/static", StaticFiles(directory="../front"), name="static")

# 📌 템플릿 설정 (front.html 경로)
templates = Jinja2Templates(directory="../front")

@app.get("/", response_class=HTMLResponse)
async def serve_front(request: Request):
    return templates.TemplateResponse("front.html", {"request": request})

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

def extract_recommendation_items(text: str) -> list[str]:
    # 빈 줄 기준으로 항목 나누기
    return [item.strip() for item in text.split("\n") if item.strip()]


def extract_place_names(text: str) -> list[str]:
    items = extract_recommendation_items(text)
    place_names = []

    # 장소명 후보가 되는 라인만 필터링: 콜론 없고 짧은 줄
    for line in items:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            continue
        if len(line.split()) > 10:  # 너무 긴 문장 제거
            continue
        if any(char.isdigit() for char in line):  # 숫자 포함된 줄은 제외 (가격 등)
            continue
        if line.lower().startswith("note"):
            continue
        place_names.append(line)

    # 중복 제거 (예: AI가 같은 문장을 두 번 주는 경우)
    return list(dict.fromkeys(place_names))

@app.get("/weather", response_class=HTMLResponse)
async def weather(
    request: Request,
    loc: str = Query(..., example="Seoul"),
    budget_krw: float = Query(0.0, description="Budget in KRW.")
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return HTMLResponse(content="<h3>Location not found.</h3>", status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return HTMLResponse(content=f"<h3>Weather API error: {weather_data.get('message', 'Unknown error')}</h3>", status_code=500)

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
        humidity = weather_data["main"]["humidity"]
    except KeyError as e:
        logger.error(f"Missing weather key: {str(e)}")
        return HTMLResponse(content=f"<h3>Weather data incomplete: Missing key {str(e)}</h3>", status_code=500)

    # Gemini AI 응답
    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip_cleaned = clean_ai_text(ai_tip_raw)
    recommendation_items = extract_recommendation_items(ai_tip_cleaned)

    return templates.TemplateResponse("front.html", {
        "request": request,
        "location": formatted_address,
        "temperature": temperature,
        "description": description,
        "humidity": humidity,
        "budget": f"{budget_krw:,.0f} KRW" if budget_krw > 0 else "Any",
        "recommendations": recommendation_items
    })


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


@app.get("/weather/places", response_class=JSONResponse)
def weather_places(
    loc: str = Query(...),
    budget_krw: float = Query(0.0)
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return JSONResponse(content={"error": "Location not found."}, status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        return JSONResponse(content={"error": weather_data.get("message", "Weather API error")}, status_code=500)

    try:
        temperature = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
    except KeyError as e:
        return JSONResponse(content={"error": f"Missing key {str(e)}"}, status_code=500)

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip = clean_ai_text(ai_tip_raw)
    place_names = extract_place_names(ai_tip)

    return {"places": place_names}

@app.get("/")
def root():
    return {"status": "Server is running"}