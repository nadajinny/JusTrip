from fastapi.responses import JSONResponse

@app.get("/weather/json", response_class=JSONResponse)
def weather_json(
    loc: str = Query(...),
    budget_krw: float = Query(0.0)
):
    lat, lon, formatted_address = get_coordinates(loc)
    if lat is None:
        return JSONResponse({"error": "Location not found."}, status_code=404)

    weather_data = get_weather(lat, lon)
    if weather_data.get("cod") != 200:
        message = weather_data.get("message", "Unknown error")
        return JSONResponse({"error": f"Weather API error: {message}"}, status_code=500)

    temperature = weather_data["main"]["temp"]
    description = weather_data["weather"][0]["description"]

    ai_tip_raw = get_ai_recommendation(formatted_address, description, temperature, lat, lon, budget_krw)
    ai_tip_clean = clean_ai_text(ai_tip_raw)

    # 🔥 여기서 딕셔너리로 정제
    ai_data = parse_ai_markdown_to_dict(ai_tip_clean)

    weather_info = {
        "Location": formatted_address,
        "Temperature": temperature,
        "Description": description,
        "Humidity": weather_data["main"]["humidity"]
    }

    return JSONResponse({
        "weather": weather_info,
        "ai_recommendation": ai_data
    })
