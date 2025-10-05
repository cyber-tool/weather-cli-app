import os
import requests
from dotenv import load_dotenv
from typing import Any, Optional
from colorama import Fore, Style, init

# Initialize color output for Windows
init(autoreset=True)

# Load environment variables
load_dotenv()

# Provider API keys (if available)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")
VISUALCROSSING_API_KEY = os.getenv("VISUALCROSSING_API_KEY")
# (You can add more providers and keys here)

# URLs / endpoints for each provider
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHERAPI_URL = "https://api.weatherapi.com/v1/current.json"
VISUALCROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Cache to prevent redundant API calls
weather_cache: dict[str, dict[str, Any]] = {}


class WeatherProviderError(Exception):
    """Indicates that a provider could not return data (e.g. error or missing key)."""
    pass


def fetch_openweather(city: str, units: str) -> dict[str, Any]:
    """Fetch from OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        raise WeatherProviderError("No OpenWeather API key configured")
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
    }
    resp = requests.get(OWM_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("cod") != 200:
        raise WeatherProviderError(data.get("message", "OpenWeather API error"))
    # Normalize to a common schema
    return {
        "provider": "openweather",
        "data": data
    }


def fetch_weatherapi(city: str, units: str) -> dict[str, Any]:
    """Fetch from WeatherAPI.com."""
    if not WEATHERAPI_API_KEY:
        raise WeatherProviderError("No WeatherAPI key configured")
    # WeatherAPI uses separate fields for Celsius vs Fahrenheit
    # We ignore units param and convert if needed (or pass &aqi=no)
    params = {
        "key": WEATHERAPI_API_KEY,
        "q": city,
        "aqi": "no",
    }
    resp = requests.get(WEATHERAPI_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Handle errors
    if "error" in data:
        raise WeatherProviderError(data["error"].get("message", "WeatherAPI error"))
    return {
        "provider": "weatherapi",
        "data": data
    }


def fetch_visualcrossing(city: str, units: str) -> dict[str, Any]:
    """Fetch from Visual Crossing API."""
    if not VISUALCROSSING_API_KEY:
        raise WeatherProviderError("No Visual Crossing key configured")
    # Visual Crossing uses a “timeline” endpoint; for current we request today
    # Units: metric or us (imperial)
    unit_group = "metric" if units == "metric" else "us"
    url = f"{VISUALCROSSING_URL}/{city}"
    params = {
        "unitGroup": unit_group,
        "key": VISUALCROSSING_API_KEY,
        "include": "current",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # Check for errors
    if "errorCode" in data:
        raise WeatherProviderError(data.get("message", "Visual Crossing error"))
    return {
        "provider": "visualcrossing",
        "data": data
    }


def fetch_open_meteo(lat: float, lon: float, units: str) -> dict[str, Any]:
    """Fetch from Open-Meteo (no API key required) as fallback."""
    # Open-Meteo’s “current weather” endpoint
    # It returns e.g. “temperature” in Celsius; if units = imperial, convert later
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "provider": "open-meteo",
        "data": data
    }


def get_weather(city: str, units: str = "metric") -> dict[str, Any]:
    """Try available providers in order until one returns valid data."""
    # Use caching
    cache_key = f"{city.lower()}_{units}"
    if cache_key in weather_cache:
        return weather_cache[cache_key]

    # Attempt providers in order of preference
    errors = []
    for fetcher in (fetch_openweather, fetch_weatherapi, fetch_visualcrossing):
        try:
            result = fetcher(city, units)
            weather_cache[cache_key] = result
            return result
        except WeatherProviderError as wpe:
            errors.append(f"{fetcher.__name__}: {wpe}")
        except requests.RequestException as re:
            errors.append(f"{fetcher.__name__}: network error {re}")

    # As fallback, try open-meteo if we can geocode city to lat/lon
    # Simple geocoding via OpenWeather if key exists
    if OPENWEATHER_API_KEY:
        try:
            # Use OWM geocoding API
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                "q": city,
                "limit": 1,
                "appid": OPENWEATHER_API_KEY,
            }
            r = requests.get(geo_url, params=geo_params, timeout=5)
            r.raise_for_status()
            glist = r.json()
            if glist:
                lat = glist[0]["lat"]
                lon = glist[0]["lon"]
                om = fetch_open_meteo(lat, lon, units)
                weather_cache[cache_key] = om
                return om
        except Exception as ge:
            errors.append(f"open_meteo fallback geocode: {ge}")

    # If all fail:
    err_msg = "All weather providers failed:\n" + "\n".join(errors)
    raise RuntimeError(err_msg)


def display_weather(resp_struct: dict[str, Any], units: str) -> None:
    """Display weather info in a unified way, adapting per provider."""
    provider = resp_struct.get("provider", "unknown")
    d = resp_struct.get("data", {})

    temp_unit = "°C" if units == "metric" else "°F"
    print(f"\n{Fore.CYAN}---- Weather Report ({provider}) ----{Style.RESET_ALL}")

    if provider == "openweather":
        city = d.get("name", "?")
        country = d.get("sys", {}).get("country", "?")
        main = d.get("main", {})
        wind = d.get("wind", {})
        weather = d.get("weather", [{}])[0]
        print(f"{Fore.YELLOW}City:{Style.RESET_ALL} {city}, {country}")
        print(f"{Fore.YELLOW}Temperature:{Style.RESET_ALL} {main.get('temp', '?')} {temp_unit}")
        print(f"{Fore.YELLOW}Feels Like:{Style.RESET_ALL} {main.get('feels_like', '?')} {temp_unit}")
        print(f"{Fore.YELLOW}Humidity:{Style.RESET_ALL} {main.get('humidity', '?')}%")
        print(f"{Fore.YELLOW}Weather:{Style.RESET_ALL} {weather.get('description', 'N/A').title()}")
        print(f"{Fore.YELLOW}Wind Speed:{Style.RESET_ALL} {wind.get('speed', '?')} m/s")

    elif provider == "weatherapi":
        loc = d.get("location", {})
        curr = d.get("current", {})
        city = loc.get("name", "?")
        country = loc.get("country", "?")
        # Temperature fields: temp_c, temp_f
        temp = curr.get("temp_c") if units == "metric" else curr.get("temp_f")
        feels = curr.get("feelslike_c") if units == "metric" else curr.get("feelslike_f")
        print(f"{Fore.YELLOW}City:{Style.RESET_ALL} {city}, {country}")
        print(f"{Fore.YELLOW}Temperature:{Style.RESET_ALL} {temp} {temp_unit}")
        print(f"{Fore.YELLOW}Feels Like:{Style.RESET_ALL} {feels} {temp_unit}")
        print(f"{Fore.YELLOW}Humidity:{Style.RESET_ALL} {curr.get('humidity', '?')}%")
        print(f"{Fore.YELLOW}Weather:{Style.RESET_ALL} {curr.get('condition', {}).get('text', 'N/A')}")
        print(f"{Fore.YELLOW}Wind Speed:{Style.RESET_ALL} {(curr.get('wind_kph', '?') / 3.6) if units == 'metric' else curr.get('wind_mph', '?')} m/s")

    elif provider == "visualcrossing":
        # Visual Crossing “currentConditions” is under data["currentConditions"]
        city = d.get("address", "?")
        cc = d.get("currentConditions", {})
        temp = cc.get("temp")
        feels = cc.get("feelslike")
        humidity = cc.get("humidity")
        wind = cc.get("windspeed")
        conditions = cc.get("conditions")
        print(f"{Fore.YELLOW}City:{Style.RESET_ALL} {city}")
        print(f"{Fore.YELLOW}Temperature:{Style.RESET_ALL} {temp} {temp_unit}")
        print(f"{Fore.YELLOW}Feels Like:{Style.RESET_ALL} {feels} {temp_unit}")
        print(f"{Fore.YELLOW}Humidity:{Style.RESET_ALL} {humidity}%")
        print(f"{Fore.YELLOW}Weather:{Style.RESET_ALL} {conditions}")
        print(f"{Fore.YELLOW}Wind Speed:{Style.RESET_ALL} {wind} m/s")

    elif provider == "open-meteo":
        # Open-Meteo returns "current_weather"
        cw = d.get("current_weather", {})
        temp_c = cw.get("temperature")
        # It gives speed in m/s
        wind = cw.get("windspeed")
        # No feels or humidity by default
        print(f"{Fore.YELLOW}Temperature:{Style.RESET_ALL} {temp_c} °C")
        print(f"{Fore.YELLOW}Wind Speed:{Style.RESET_ALL} {wind} m/s")

    else:
        print("Unhandled provider. Raw data:")
        print(d)

    print(f"{Fore.CYAN}------------------------------{Style.RESET_ALL}\n")


def main() -> None:
    """Run the Weather CLI application."""
    print(f"{Fore.MAGENTA}🌦️  Welcome to Weather CLI App 🌦️{Style.RESET_ALL}")
    try:
        while True:
            city = input("\nEnter city name (or type 'exit' to quit): ").strip()
            if city.lower() == "exit":
                print(f"{Fore.GREEN}Goodbye! 👋{Style.RESET_ALL}")
                break

            if not city:
                print(f"{Fore.RED}⚠️  City name cannot be empty. Please try again.{Style.RESET_ALL}")
                continue

            units_choice = input("Choose units - Celsius (c) or Fahrenheit (f): ").lower().strip()
            units = "metric" if units_choice == "c" else "imperial"

            try:
                weather_resp = get_weather(city, units)
                display_weather(weather_resp, units)
            except Exception as e:
                print(f"{Fore.RED}⚠️  {e}{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Goodbye! 👋{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
