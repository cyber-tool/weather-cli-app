import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str, units: str = "metric") -> dict:
    """
    Fetch current weather data for a given city.
    """
    params = {
        "q": city,
        "appid": API_KEY,
        "units": units
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Error fetching weather: {response.json().get('message', 'Unknown error')}")
    
    return response.json()


def display_weather(data: dict, units: str):
    """
    Display weather details in a readable format.
    """
    temp_unit = "°C" if units == "metric" else "°F"
    print("\n---- Weather Report ----")
    print(f"City: {data['name']}, {data['sys']['country']}")
    print(f"Temperature: {data['main']['temp']} {temp_unit}")
    print(f"Feels like: {data['main']['feels_like']} {temp_unit}")
    print(f"Humidity: {data['main']['humidity']}%")
    print(f"Weather: {data['weather'][0]['description'].title()}")
    print(f"Wind Speed: {data['wind']['speed']} m/s")
    print("------------------------\n")


def main():
    print("🌦️ Welcome to Weather CLI App 🌦️")

    while True:
        city = input("Enter city name (or type 'exit' to quit): ").strip()
        if city.lower() == "exit":
            print("Goodbye! 👋")
            break

        units_choice = input("Choose units - Celsius (c) or Fahrenheit (f): ").lower()
        units = "metric" if units_choice == "c" else "imperial"

        try:
            weather_data = get_weather(city, units)
            display_weather(weather_data, units)
        except Exception as e:
            print(f"⚠️ {e}")


if __name__ == "__main__":
    main()
