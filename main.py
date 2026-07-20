import os
# 1. Import the dotenv loader
from dotenv import load_dotenv

# 2. Fire it up immediately before importing internal modules
load_dotenv()

# 3. Now it is safe to import agent logic
from langchain_core.messages import HumanMessage
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
    
    initial_input = {
        "messages": [HumanMessage(content=user_prompt)]
    }

    # Run execution engine
    output = travel_app.invoke(initial_input)
    
    print("\n--- Agent Response ---")
    print(output["messages"][-1].content)

if __name__ == "__main__":
    run_agent()