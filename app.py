import os
import re
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from agent import travel_app

FARE_LINE_RE = re.compile(
    r"^- (?P<label>\S.*?): \$(?P<price>[\d.]+)(?P<original> \(originally requested\))?$"
)


def parse_flexible_fare_table(text: str):
    """Turn fetch_flexible_dates' plain-text summary into a DataFrame for charting."""
    rows = []
    for line in text.splitlines():
        match = FARE_LINE_RE.match(line.strip())
        if match:
            rows.append({
                "Dates": match.group("label"),
                "Price (CAD)": float(match.group("price")),
                "Selected": bool(match.group("original")),
            })
    return pd.DataFrame(rows) if rows else None

st.set_page_config(page_title="AI Travel Agent", page_icon="✈️")
st.title("✈️ Autonomous Flight Booker")
st.markdown("Enter your itinerary below, and the agent will dynamically search live airline data.")

# Removed the 'with st.form("flight_form"):' wrapper so widgets can instantly interact
col1, col2 = st.columns(2)

with col1:
    origin = st.text_input("Departure City or Airport Code", value="Toronto (YYZ)")
    departure_date = st.date_input("Leaving Date")
    
    class_options = {
        "Economy": 1, 
        "Premium Economy": 2, 
        "Business": 3, 
        "First Class": 4
    }
    selected_class = st.selectbox("Cabin Class", options=class_options.keys())

with col2:
    destination = st.text_input("Destination City or Airport Code", value="London (LHR)")
    
    # --- Checkbox to toggle one-way vs round-trip ---
    is_one_way = st.checkbox("One-way trip (no return date)")
    
    # This will now instantly trigger a UI update when clicked
    if not is_one_way:
        return_date = st.date_input("Returning Date")
    else:
        return_date = None
        
    adults = st.number_input("Number of Travelers", min_value=1, max_value=9, value=1)

check_flexible_dates = st.checkbox(
    "Also check ±2 days around my dates for cheaper fares",
    help="Runs extra searches on nearby dates and reports if shifting your trip would be cheaper."
)

# Replaced the form submit button with a standard button
submit = st.button("Search Flights", type="primary")

if submit:
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        st.error("Missing API Keys! Check your .env file.")
        st.stop()
        
    if not is_one_way and departure_date > return_date:
        st.error("Return date cannot be before departure date.")
        st.stop()

    with st.spinner("Agent is searching live databases..."):
        
        if is_one_way:
            prompt = (
                f"Find the cheapest one-way flights from {origin} to {destination}. "
                f"Departing on {departure_date}. "
                f"There are {adults} passengers flying in {selected_class} class. "
                f"Map the travel class to the correct integer constraint."
            )
        else:
            prompt = (
                f"Find the cheapest round-trip flights from {origin} to {destination}. "
                f"Departing on {departure_date} and returning on {return_date}. "
                f"There are {adults} passengers flying in {selected_class} class. "
                f"Map the travel class to the correct integer constraint."
            )

        if check_flexible_dates:
            prompt += (
                " After that, also call fetch_flexible_dates with the same route, class, and "
                "passenger count to check fares 2 days before and after my date(s), and tell me "
                "whether shifting my trip would save money."
            )

        today = datetime.now().strftime("%Y-%m-%d")
        
        initial_input = {
            "messages": [
                SystemMessage(content=f"You are a helpful travel assistant. Today's date is {today}. Use this to determine the correct year for any flight requests."),
                HumanMessage(content=prompt)
            ]
        }

        output = travel_app.invoke(initial_input)
        response_content = output["messages"][-1].content

        flexible_fare_df = None
        for message in output["messages"]:
            if isinstance(message, ToolMessage) and message.name == "fetch_flexible_dates":
                flexible_fare_df = parse_flexible_fare_table(message.content)

        st.subheader("Agent Findings")

        if isinstance(response_content, str):
            st.markdown(response_content)
        elif isinstance(response_content, list):
            for block in response_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    st.markdown(block.get("text"))
                elif isinstance(block, str):
                    st.markdown(block)

        if flexible_fare_df is not None:
            st.subheader("Nearby Date Fares")
            st.bar_chart(flexible_fare_df.set_index("Dates")["Price (CAD)"])
            st.dataframe(flexible_fare_df, hide_index=True, width="stretch")