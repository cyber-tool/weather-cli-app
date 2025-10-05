import os
import requests
from dotenv import load_dotenv
from typing import Dict, Optional

# Load environment variables
load_dotenv()

# Configuration: API keys (or flags) for various providers
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHERAPI_API_KEY = os.getenv("WEATHERAPI_API_KEY")
WEATHERBIT_API_KEY = os.getenv("WEATHERBIT_API_KEY")
# Open-Meteo doesn’t require an API key (free and open) :contentReference[oaicite:0]{index=0}

class WeatherProvider:
    """Abstract base class for weather providers."""
    def get_weather(self, city: str, units: str) -> Dict:
        raise NotImplementedError

class OpenWeatherProvider(WeatherProvider):
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    def get_weather(self, city: str, units: str) -> Dict:
        if not OPENWEATHER_API_KEY:
            raise ValueError("Missing OPENWEATHER_API_KEY")
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": units}
        resp = requests.get(self.BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"OpenWeather error: {resp.json().get('message')}")
        return resp.json()

class WeatherAPIProvider(WeatherProvider):
    BASE_URL = "http://api.weatherapi.com/v1/current.json"
    def get_weather(self, city: str, units: str) -> Dict:
        if not WEATHERAPI_API_KEY:
            raise ValueError("Missing WEATHERAPI_API_KEY")
        # WeatherAPI uses "key" and returns temp_c / temp_f
        params = {"key": WEATHERAPI_API_KEY, "q": city}
        resp = requests.get(self.BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"WeatherAPI error: {resp.json().get('error', {}).get('message')}")
        return resp.json()

class WeatherbitProvider(WeatherProvider):
    BASE_URL = "https://api.weatherbit.io/v2.0/current"
    def get_weather(self, city: str, units: str) -> Dict:
        if not WEATHERBIT_API_KEY:
            raise ValueError("Missing WEATHERBIT_API_KEY")
        # Weatherbit uses units param "units" with m or i
        ub = "M" if units == "metric" else "I"
        params = {"city": city, "key": WEATHERBIT_API_KEY, "units": ub}
        resp = requests.get(self.BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Weatherbit error: {resp.json().get('error', {}).get('message')}")
        return resp.json()

class OpenMeteoProvider(WeatherProvider):
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    def get_weather(self, city: str, units: str) -> Dict:
        # Open-Meteo requires latitude & longitude; we need a geocoding step
        lat, lon = geocode_city(city)
        # For simplicity only request current data
        # documentation: &current_weather=true :contentReference[oaicite:1]{index=1}
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
        }
        # Units: Open-Meteo returns temperature in °C and wind in m/s; no imperial support
        resp = requests.get(self.BASE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"OpenMeteo error: {resp.json().get('reason', '')}")
        return resp.json()

def geocode_city(city: str) -> (float, float):
    """
    Simple geocoding fallback: Use OpenWeather’s geocoding if OPENWEATHER_API_KEY is available,
    else use WeatherAPI geocoding, else error.
    """
    # Try OpenWeather geocoding
    if OPENWEATHER_API_KEY:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    # Try WeatherAPI geocoding
    if WEATHERAPI_API_KEY:
        url = "http://api.weatherapi.com/v1/search.json"
        params = {"key": WEATHERAPI_API_KEY, "q": city}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    raise ValueError(f"Unable to geocode city '{city}' — no geocoding provider available")

def pick_provider() -> WeatherProvider:
    """
    Pick a provider in the following precedence if its configuration is available:
    1. OpenWeather
    2. WeatherAPI
    3. Weatherbit
    4. OpenMeteo (always available, no key needed)
    """
    # We prefer providers in an order; you can reorder as needed
    if OPENWEATHER_API_KEY:
        return OpenWeatherProvider()
    if WEATHERAPI_API_KEY:
        return WeatherAPIProvider()
    if WEATHERBIT_API_KEY:
        return WeatherbitProvider()
    # fallback:
    return OpenMeteoProvider()

def get_weather(city: str, units: str = "metric") -> Dict:
    provider = pick_provider()
    return provider.get_weather(city, units)

def display_weather(data: Dict, units: str) -> None:
    temp_unit = "°C" if units == "metric" else "°F"
    print("\n---- Weather Report ----")

    # Different APIs have different response formats:
    # Try to handle few cases:
    if "name" in data and "main" in data:
        # Likely OpenWeather
        print(f"City: {data['name']}, {data['sys']['country']}")
        print(f"Temperature: {data['main']['temp']} {temp_unit}")
        print(f"Feels Like: {data['main']['feels_like']} {temp_unit}")
        print(f"Humidity: {data['main']['humidity']}%")
        print(f"Weather: {data['weather'][0]['description'].title()}")
        print(f"Wind Speed: {data['wind']['speed']} m/s")
    elif "location" in data and "current" in data:
        # Likely WeatherAPI
        loc = data["location"]
        cur = data["current"]
        print(f"City: {loc['name']}, {loc['country']}")
        t = cur["temp_c"] if units == "metric" else cur["temp_f"]
        feels = cur["feelslike_c"] if units == "metric" else cur["feelslike_f"]
        print(f"Temperature: {t} {temp_unit}")
        print(f"Feels Like: {feels} {temp_unit}")
        print(f"Humidity: {cur['humidity']}%")
        print(f"Weather: {cur['condition']['text']}")
        print(f"Wind Speed: {cur['wind_kph'] / 3.6 if units == 'metric' else cur['wind_mph']} m/s")
    elif "data" in data and isinstance(data["data"], list):
        # Likely Weatherbit
        rec = data["data"][0]
        print(f"City: {rec['city_name']}, {rec.get('country_code', '')}")
        print(f"Temperature: {rec['temp']} {temp_unit}")
        print(f"Humidity: {rec['rh']}%")
        print(f"Weather: {rec['weather']['description']}")
        print(f"Wind Speed: {rec['wind_spd']} m/s")
    elif "current_weather" in data:
        # Open-Meteo
        cw = data["current_weather"]
        lat = data.get("latitude")
        lon = data.get("longitude")
        print(f"City: (lat {lat}, lon {lon})")
        print(f"Temperature: {cw['temperature']} °C")  # only Celsius
        print(f"Wind Speed: {cw['windspeed']} m/s")
    else:
        print("⚠️ Unknown data format:")
        print(data)

    print("------------------------\n")

def main() -> None:
    print("🌦️ Welcome to Weather CLI App 🌦️")
    try:
        while True:
            city = input("Enter city name (or type 'exit' to quit): ").strip()
            if city.lower() == "exit":
                print("Goodbye! 👋")
                break
            if not city:
                print("⚠️ City name cannot be empty. Please try again.")
                continue

            units_choice = input("Choose units — Celsius (c) or Fahrenheit (f): ").lower()
            units = "metric" if units_choice == "c" else "imperial"

            try:
                weather_data = get_weather(city, units)
                display_weather(weather_data, units)
            except Exception as e:
                print(f"⚠️ {e}")
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")

if __name__ == "__main__":
    main()
