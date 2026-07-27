from geopy.geocoders import Nominatim

def get_coordinates(location):
    geolocator = Nominatim(user_agent="weather-simulator-app")
    location_result = geolocator.geocode(location)
    if location_result is None:
        raise ValueError(f"Location not found: {location}")
    return location_result.latitude, location_result.longitude
