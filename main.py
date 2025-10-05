import os
import requests
from dotenv import load_dotenv
from typing import Any
from colorama import Fore, Style, init

# Initialize color output for Windows
init(autoreset=True)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Cache to prevent redundant API calls
weather_cache: dict[str, dict[str, Any]] = {}


def get_weather(city: str, units: str = "metric") -> dict[str, Any]:
    """Fetch current weather data for a given city using the OpenWeatherMap API."""
    if not API_KEY:
        raise ValueError("Missing API key. Please set OPENWEATHER_API_KEY in your .env file.")

    # Check cache first
    cache_key = f"{city.lower()}_{units}"
    if cache_key in weather_cache:
        return weather_cache[cache_key]

    params = {
        "q": city,
        "appid": API_KEY,
        "units": units,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad status
        data = response.json()

        # Check for API-level errors
        if data.get("cod") != 200:
            raise ValueError(data.get("message", "Unknown error from API"))

        # Store in cache
        weather_cache[cache_key] = data
        return data

    except requests.exceptions.Timeout:
        raise TimeoutError("Request timed out. Please check your connection.")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Network error: {e}")


def display_weather(data: dict[str, Any], units: str) -> None:
    """Display weather details in a user-friendly format."""
    temp_unit = "°C" if units == "metric" else "°F"

    city = data.get("name", "Unknown City")
    country = data.get("sys", {}).get("country", "N/A")
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]

    print(f"\n{Fore.CYAN}---- Weather Report ----{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}City:{Style.RESET_ALL} {city}, {country}")
    print(f"{Fore.YELLOW}Temperature:{Style.RESET_ALL} {main.get('temp', '?')} {temp_unit}")
    print(f"{Fore.YELLOW}Feels Like:{Style.RESET_ALL} {main.get('feels_like', '?')} {temp_unit}")
    print(f"{Fore.YELLOW}Humidity:{Style.RESET_ALL} {main.get('humidity', '?')}%")
    print(f"{Fore.YELLOW}Weather:{Style.RESET_ALL} {weather.get('description', 'N/A').title()}")
    print(f"{Fore.YELLOW}Wind Speed:{Style.RESET_ALL} {wind.get('speed', '?')} m/s")
    print(f"{Fore.CYAN}------------------------{Style.RESET_ALL}\n")


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
                weather_data = get_weather(city, units)
                display_weather(weather_data, units)
            except Exception as e:
                print(f"{Fore.RED}⚠️  {e}{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Goodbye! 👋{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
