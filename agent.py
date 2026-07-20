from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Import the tool we created in tools.py
from tools import fetch_google_flights

# 1. State Definition
class TravelAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    search_params: Dict[str, Any]
    flight_results: List[Dict[str, Any]]

# 2. Initialization 
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
llm_with_tools = llm.bind_tools([fetch_google_flights])

# 3. Graph Nodes
def call_agent_router(state: TravelAgentState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def execute_tools(state: TravelAgentState):
    last_message = state["messages"][-1]
    tool_outputs = []
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "fetch_google_flights":
            res = fetch_google_flights.invoke(tool_call["args"])
            tool_outputs.append(res)
            
    return {"messages": tool_outputs}

# 4. Conditional Routing Logic
def should_continue(state: TravelAgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# 5. Graph Construction
workflow = StateGraph(TravelAgentState)

workflow.add_node("agent", call_agent_router)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

# Export the compiled application
travel_app = workflow.compile()