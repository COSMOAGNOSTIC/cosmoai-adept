import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.config import OPENWEATHER_API_KEY


class WeatherInput(BaseModel):
    city: str = Field(description="City name to get current weather for")


@tool(args_schema=WeatherInput)
def get_weather(city: str) -> str:
    """Get current weather conditions for a city."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return f"Weather API error: {response.status_code} - {response.text}"
        data = response.json()
        desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        return (
            f"{city}: {desc}\n"
            f"Temp: {temp}\u00b0F (feels like {feels}\u00b0F)\n"
            f"Humidity: {humidity}%\n"
            f"Wind: {wind} mph"
        )
    except requests.exceptions.Timeout:
        return "Weather request timed out."
    except Exception as e:
        return f"Weather lookup failed: {e}"
