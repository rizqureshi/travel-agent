import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from agent import travel_app

def check_environment():
    """Ensure required credentials are bound to local process context."""
    missing = []
    if not os.getenv("GOOGLE_API_KEY"):
        missing.append("GOOGLE_API_KEY")
    if not os.getenv("SERPAPI_API_KEY"):
        missing.append("SERPAPI_API_KEY")
        
    if missing:
        print(f"CRITICAL ERROR: Missing environment credentials: {', '.join(missing)}")
        print("Please check your local .env configuration file settings.")
        return False
    return True

def run_agent():
    if not check_environment():
        return

    print("Initializing Flight Engine Search Agent...")
    
    user_prompt = "Find me the business class flights from Toronto to London leaving on September 15 and returning on September 29."
    
    # 1. Grab the current system date dynamically
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 2. Inject a SystemMessage to ground the LLM's timeline
    initial_input = {
        "messages": [
            SystemMessage(content=f"You are a helpful travel assistant. Today's date is {today}. Use this to determine the correct year for any flight requests."),
            HumanMessage(content=user_prompt)
        ]
    }

    # Run execution engine
    output = travel_app.invoke(initial_input)
    
    print("\n--- Agent Response ---")
    # Extract the raw content
    response_content = output["messages"][-1].content
    
    # 1. If the model returned a simple string, print it directly
    if isinstance(response_content, str):
        print(response_content)
        
    # 2. If the model returned a list of content blocks, extract the text
    elif isinstance(response_content, list):
        for block in response_content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text"))
            # Fallback just in case a block is a raw string
            elif isinstance(block, str):
                print(block)

if __name__ == "__main__":
    run_agent()