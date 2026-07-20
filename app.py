import os
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from agent import travel_app

st.set_page_config(page_title="AI Travel Agent", page_icon="✈️")
st.title("✈️ Autonomous Flight Booker")
st.markdown("Enter your itinerary below, and the agent will dynamically search live airline data.")

with st.form("flight_form"):
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
        
        # Only show return date picker if it's NOT a one-way trip
        if not is_one_way:
            return_date = st.date_input("Returning Date")
        else:
            return_date = None
            
        adults = st.number_input("Number of Travelers", min_value=1, max_value=9, value=1)
        
    submit = st.form_submit_button("Search Flights")

if submit:
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        st.error("Missing API Keys! Check your .env file.")
        st.stop()
        
    if not is_one_way and departure_date > return_date:
        st.error("Return date cannot be before departure date.")
        st.stop()

    with st.spinner("Agent is searching live databases..."):
        
        # Dynamically phrase prompt based on trip type
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
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        initial_input = {
            "messages": [
                SystemMessage(content=f"You are a helpful travel assistant. Today's date is {today}. Use this to determine the correct year for any flight requests."),
                HumanMessage(content=prompt)
            ]
        }

        output = travel_app.invoke(initial_input)
        response_content = output["messages"][-1].content

        st.subheader("Agent Findings")
        
        if isinstance(response_content, str):
            st.markdown(response_content)
        elif isinstance(response_content, list):
            for block in response_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    st.markdown(block.get("text"))
                elif isinstance(block, str):
                    st.markdown(block)