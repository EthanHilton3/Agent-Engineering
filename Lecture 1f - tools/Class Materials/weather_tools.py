import json
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tools import ToolBox


toolbox = ToolBox()


WEATHER_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "light snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with light hail",
    99: "thunderstorm with heavy hail",
}


def _get_json(url: str, params: dict[str, str] | None = None) -> dict:
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "CS301-tool-calling-demo/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except Exception as error:
        raise RuntimeError(f"request failed for {url}: {error}") from error


@toolbox.tool
def get_current_location() -> str:
    """Estimate the caller's current location from the machine's public IP address."""
    result = _get_json("https://ipapi.co/json/")
    if result.get("error"):
        raise RuntimeError(result.get("reason", "location lookup failed"))

    location = {
        "city": result.get("city"),
        "region": result.get("region"),
        "country": result.get("country_name"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),
        "approximate": True,
    }
    if location["latitude"] is None or location["longitude"] is None:
        raise RuntimeError("location service did not return coordinates")
    return json.dumps(location)


@toolbox.tool
def get_current_weather(
    latitude: float,
    longitude: float,
    temperature_unit: Literal["fahrenheit", "celsius"],
) -> str:
    """Retrieve current weather for coordinates from the Open-Meteo API."""
    result = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,weather_code,wind_speed_10m",
            "temperature_unit": temperature_unit,
            "wind_speed_unit": "mph" if temperature_unit == "fahrenheit" else "kmh",
            "timezone": "auto",
        },
    )
    current = result.get("current") or {}
    current["condition"] = WEATHER_DESCRIPTIONS.get(
        current.get("weather_code"), "unknown conditions"
    )
    return json.dumps({
        "source": "Open-Meteo",
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone"),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "current": current,
        "current_units": result.get("current_units"),
    })
