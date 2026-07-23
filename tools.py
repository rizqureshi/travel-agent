import os
import requests
from datetime import datetime, timedelta
from langchain_core.tools import tool

SERPAPI_URL = "https://serpapi.com/search"


def _search_flights(departure_id, arrival_id, outbound_date, return_date, travel_class, adults):
    """Shared SerpApi request logic. Returns (data, error_message)."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return None, "Error: Missing SERPAPI_API_KEY environment variable."

    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "travel_class": travel_class,
        "adults": adults,
        "currency": "CAD",
        "api_key": api_key,
    }
    if return_date and return_date != "None":
        params["return_date"] = return_date

    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        return None, f"Failed to retrieve flights due to an API error: {str(e)}"

    if data.get("error"):
        return None, f"SerpApi error: {data['error']}"

    return data, None


def _cheapest_price(data):
    candidates = data.get("best_flights", []) + data.get("other_flights", [])
    prices = [f["price"] for f in candidates if isinstance(f.get("price"), (int, float))]
    return min(prices) if prices else None


@tool
def fetch_google_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str = None,
    travel_class: int = 1,
    adults: int = 1
) -> str:
    """
    Queries live flight options via SerpApi Google Flights engine.
    Args:
        departure_id: 3-letter uppercase IATA code for departure airport (e.g., 'YYZ')
        arrival_id: 3-letter uppercase IATA code for destination airport (e.g., 'LHR')
        outbound_date: Departure date in YYYY-MM-DD format.
        return_date: Optional return date in YYYY-MM-DD format for round trips. Pass None if one-way.
        travel_class: 1 for Economy, 2 for Premium Economy, 3 for Business, 4 for First.
        adults: Number of adult passengers.
    """
    data, error = _search_flights(departure_id, arrival_id, outbound_date, return_date, travel_class, adults)
    if error:
        return error

    best = data.get("best_flights", [])
    if not best:
        return "No direct 'best flights' found for this combination."

    return str(best[:3])


@tool
def fetch_flexible_dates(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str = None,
    travel_class: int = 1,
    adults: int = 1,
    flex_days: int = 2
) -> str:
    """
    Compares the cheapest fare on the requested date(s) against fares a few days
    earlier and later, to reveal whether shifting the trip saves money. For round
    trips, the outbound and return dates are shifted together by the same number of
    days so the trip length is preserved.
    Args:
        departure_id: 3-letter uppercase IATA code for departure airport (e.g., 'YYZ')
        arrival_id: 3-letter uppercase IATA code for destination airport (e.g., 'LHR')
        outbound_date: Requested departure date in YYYY-MM-DD format.
        return_date: Optional requested return date in YYYY-MM-DD format. Pass None if one-way.
        travel_class: 1 for Economy, 2 for Premium Economy, 3 for Business, 4 for First.
        adults: Number of adult passengers.
        flex_days: How many days before/after the requested date(s) to check (default 2).
    """
    try:
        base_out = datetime.strptime(outbound_date, "%Y-%m-%d")
    except ValueError:
        return f"Error: outbound_date '{outbound_date}' is not in YYYY-MM-DD format."

    base_ret = None
    if return_date and return_date != "None":
        try:
            base_ret = datetime.strptime(return_date, "%Y-%m-%d")
        except ValueError:
            return f"Error: return_date '{return_date}' is not in YYYY-MM-DD format."

    rows = []
    for delta in range(-flex_days, flex_days + 1):
        shifted_out_str = (base_out + timedelta(days=delta)).strftime("%Y-%m-%d")
        shifted_ret_str = (base_ret + timedelta(days=delta)).strftime("%Y-%m-%d") if base_ret else None

        data, _ = _search_flights(
            departure_id, arrival_id, shifted_out_str, shifted_ret_str, travel_class, adults
        )
        price = _cheapest_price(data) if data else None
        rows.append((delta, shifted_out_str, shifted_ret_str, price))

    priced_rows = [r for r in rows if r[3] is not None]
    if not priced_rows:
        return "Could not retrieve comparable fares for nearby dates."

    cheapest = min(priced_rows, key=lambda r: r[3])
    original = next((r for r in rows if r[0] == 0), None)

    lines = ["Fare comparison for nearby dates (CAD):"]
    for delta, out_str, ret_str, price in rows:
        label = out_str if not ret_str else f"{out_str} -> {ret_str}"
        price_str = f"${price}" if price is not None else "unavailable"
        tag = " (originally requested)" if delta == 0 else ""
        lines.append(f"- {label}: {price_str}{tag}")

    if original and original[3] is not None and cheapest[0] != 0 and cheapest[3] < original[3]:
        savings = original[3] - cheapest[3]
        cheapest_label = cheapest[1] if not cheapest[2] else f"{cheapest[1]} -> {cheapest[2]}"
        lines.append(
            f"\nCheaper option found: flying {cheapest_label} saves ${savings} CAD "
            f"compared to the originally requested date."
        )
    else:
        lines.append("\nThe originally requested date already has the cheapest fare in this range.")

    return "\n".join(lines)
