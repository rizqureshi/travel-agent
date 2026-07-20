import os
import requests
from langchain_core.tools import tool

@tool
def fetch_google_flights(
    departure_id: str, 
    arrival_id: str, 
    outbound_date: str, 
    return_date: str = None
) -> str:
    """
    Queries live flight options via SerpApi Google Flights engine.
    Args:
        departure_id: 3-letter uppercase IATA code for departure airport (e.g., 'YYZ')
        arrival_id: 3-letter uppercase IATA code for destination airport (e.g., 'LHR')
        outbound_date: Departure date in YYYY-MM-DD format.
        return_date: Optional return date in YYYY-MM-DD format for round trips.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: Missing SERPAPI_API_KEY framework environment variable."

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "currency": "CAD",
        "api_key": api_key
    }
    if return_date:
        params["return_date"] = return_date

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        best = data.get("best_flights", [])
        if not best:
            return "No direct 'best flights' found for this combination."
            
        return str(best[:3])
    except Exception as e:
        return f"Failed to retrieve flights due to an API error: {str(e)}"