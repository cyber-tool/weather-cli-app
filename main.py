import os
import requests
from dotenv import load_dotenv
from typing import Dict

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str, units: str = "metric") -> Dict:
    """
    Fetch current weather data for a given city using the OpenWeatherMap API.

    Args:
        city (str): The city name.
        units (str): Measurement units ("metric" or "imperial").

    Returns:
        dict: Weather data in JSON format.

    Raises:
        Exception: If the request fails or returns an error.
    """
    if not API_KEY:
        raise ValueError("Missing API key. Please set OPENWEATHER_API_KEY in your .env file.")

    params = {
        "q": city,
        "appid": API_KEY,
        "units": units,
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Error fetching weather: {response.json().get('message', 'Unknown error')}")

    return response.json()


def display_weather(data: Dict, units: str) -> None:
    """
    Display weather details in a user-friendly format.

    Args:
        data (dict): Weather data from API.
        units (str): Measurement units ("metric" or "imperial").
    """
    temp_unit = "°C" if units == "metric" else "°F"

    print("\n---- Weather Report ----")
    print(f"City: {data['name']}, {data['sys']['country']}")
    print(f"Temperature: {data['main']['temp']} {temp_unit}")
    print(f"Feels Like: {data['main']['feels_like']} {temp_unit}")
    print(f"Humidity: {data['main']['humidity']}%")
    print(f"Weather: {data['weather'][0]['description'].title()}")
    print(f"Wind Speed: {data['wind']['speed']} m/s")
    print("------------------------\n")


def main() -> None:
    """Run the Weather CLI application."""
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

            units_choice = input("Choose units - Celsius (c) or Fahrenheit (f): ").lower()
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
