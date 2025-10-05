import os
import json
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv
from typing import Any
from colorama import Fore, Style, init
from rich.console import Console
from rich.table import Table

# Initialize console and color output
console = Console()
init(autoreset=True)

# Load environment variables
load_dotenv()

# Provider API keys (if available)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")
VISUALCROSSING_API_KEY = os.getenv("VISUALCROSSING_API_KEY")

# URLs / endpoints
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
WEATHERAPI_URL = "https://api.weatherapi.com/v1/current.json"
WEATHERAPI_FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"
VISUALCROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Cache and logs
CACHE_FILE = "weather_cache.json"
LOG_FILE = "weather.log"
weather_cache: dict[str, dict[str, Any]] = {}
provider_stats = {"openweather": 0, "weatherapi": 0, "visualcrossing": 0, "open-meteo": 0}


class WeatherProviderError(Exception):
    pass


# ----------- Utility Functions -----------

def log_event(message: str) -> None:
    """Append log messages with timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")


def load_cache() -> None:
    """Load cached weather results."""
    global weather_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                weather_cache.update(json.load(f))
        except json.JSONDecodeError:
            pass


def save_cache() -> None:
    """Save cache to disk."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(weather_cache, f, indent=2)


def detect_location() -> str:
    """Detect approximate user location by IP."""
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=5)
        resp.raise_for_status()
        city = resp.json().get("city")
        if city:
            return city
    except Exception:
        return ""
    return ""


# ----------- Weather Providers -----------

def fetch_openweather(city: str, units: str, forecast=False):
    if not OPENWEATHER_API_KEY:
        raise WeatherProviderError("Missing OpenWeather API key.")
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": units}
    url = OWM_FORECAST_URL if forecast else OWM_URL
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("cod") not in (200, "200"):
        raise WeatherProviderError(data.get("message", "OpenWeather API error"))
    provider_stats["openweather"] += 1
    return {"provider": "openweather", "data": data}


def fetch_weatherapi(city: str, units: str, forecast=False):
    if not WEATHERAPI_API_KEY:
        raise WeatherProviderError("Missing WeatherAPI key.")
    params = {"key": WEATHERAPI_API_KEY, "q": city, "aqi": "no"}
    if forecast:
        params["days"] = 5
        url = WEATHERAPI_FORECAST_URL
    else:
        url = WEATHERAPI_URL
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise WeatherProviderError(data["error"]["message"])
    provider_stats["weatherapi"] += 1
    return {"provider": "weatherapi", "data": data}


def fetch_visualcrossing(city: str, units: str):
    if not VISUALCROSSING_API_KEY:
        raise WeatherProviderError("Missing Visual Crossing key.")
    unit_group = "metric" if units == "metric" else "us"
    url = f"{VISUALCROSSING_URL}/{city}"
    params = {"unitGroup": unit_group, "key": VISUALCROSSING_API_KEY, "include": "current"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "errorCode" in data:
        raise WeatherProviderError(data.get("message", "VisualCrossing error"))
    provider_stats["visualcrossing"] += 1
    return {"provider": "visualcrossing", "data": data}


def fetch_open_meteo(lat: float, lon: float, units: str):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "current_weather": "true"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    provider_stats["open-meteo"] += 1
    return {"provider": "open-meteo", "data": data}


# ----------- Core Weather Logic -----------

def get_weather(city: str, units="metric", forecast=False):
    cache_key = f"{city.lower()}_{units}_{forecast}"
    if cache_key in weather_cache:
        return weather_cache[cache_key]

    fetchers = [fetch_openweather, fetch_weatherapi, fetch_visualcrossing]
    errors = []
    for fetcher in sorted(fetchers, key=lambda f: -provider_stats.get(f.__name__.split("_")[1], 0)):
        try:
            result = fetcher(city, units, forecast=forecast) if "forecast" in fetcher.__code__.co_varnames else fetcher(city, units)
            weather_cache[cache_key] = result
            save_cache()
            return result
        except Exception as e:
            log_event(f"{fetcher.__name__} failed: {e}")
            errors.append(str(e))

    raise RuntimeError("All weather providers failed:\n" + "\n".join(errors))


# ----------- Display -----------

def display_weather(resp: dict[str, Any], units: str, forecast=False):
    provider = resp["provider"]
    data = resp["data"]
    temp_unit = "°C" if units == "metric" else "°F"
    console.print(f"\n[bold cyan]Weather Report ({provider})[/bold cyan]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", justify="right")
    table.add_column("Value", justify="left")

    if provider == "openweather":
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        table.add_row("City", data.get("name", "?"))
        table.add_row("Temperature", f"{main.get('temp', '?')} {temp_unit}")
        table.add_row("Humidity", f"{main.get('humidity', '?')}%")
        table.add_row("Weather", weather.get("description", "N/A").title())
    elif provider == "weatherapi":
        loc = data["location"]
        curr = data["current"]
        table.add_row("City", f"{loc['name']}, {loc['country']}")
        table.add_row("Temperature", f"{curr['temp_c'] if units == 'metric' else curr['temp_f']} {temp_unit}")
        table.add_row("Humidity", f"{curr['humidity']}%")
        table.add_row("Condition", curr["condition"]["text"])
    elif provider == "visualcrossing":
        cc = data["currentConditions"]
        table.add_row("City", data.get("address", "?"))
        table.add_row("Temperature", f"{cc.get('temp', '?')} {temp_unit}")
        table.add_row("Weather", cc.get("conditions", "N/A"))
    elif provider == "open-meteo":
        cw = data["current_weather"]
        table.add_row("Temperature", f"{cw['temperature']} °C")
        table.add_row("Windspeed", f"{cw['windspeed']} m/s")

    console.print(table)

    # Forecast summary
    if forecast and provider in ("openweather", "weatherapi"):
        console.print("\n[bold yellow]5-Day Forecast:[/bold yellow]")
        if provider == "openweather":
            for entry in data["list"][:5]:
                dt = datetime.fromtimestamp(entry["dt"]).strftime("%a %H:%M")
                desc = entry["weather"][0]["description"]
                temp = entry["main"]["temp"]
                console.print(f"• {dt}: {temp} {temp_unit}, {desc}")
        elif provider == "weatherapi":
            for d in data["forecast"]["forecastday"]:
                date = d["date"]
                condition = d["day"]["condition"]["text"]
                avg = d["day"]["avgtemp_c"] if units == "metric" else d["day"]["avgtemp_f"]
                console.print(f"• {date}: {avg}{temp_unit}, {condition}")


# ----------- CLI -----------

def main():
    parser = argparse.ArgumentParser(description="🌦️  Weather CLI App")
    parser.add_argument("city", nargs="?", help="City name (optional)")
    parser.add_argument("--units", choices=["c", "f"], default="c", help="Temperature unit")
    parser.add_argument("--forecast", action="store_true", help="Show 5-day forecast")
    args = parser.parse_args()

    load_cache()
    city = args.city or detect_location() or input("Enter city name: ").strip()
    units = "metric" if args.units == "c" else "imperial"

    try:
        resp = get_weather(city, units, forecast=args.forecast)
        display_weather(resp, units, forecast=args.forecast)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    main()
