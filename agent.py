# agent.py — Core LangChain ReAct agent for the F1 Race Strategy Agent
# Loads environment variables, wires up Google Gemini, pulls the ReAct prompt,
# and exposes a run_agent() function used by both terminal mode and bot.py.

import os                          # Standard library: read environment variables
from dotenv import load_dotenv     # Loads variables from the .env file into os.environ

# Load all keys from .env BEFORE importing LangChain/LangSmith so tracing is
# picked up automatically (LangChain reads LANGSMITH_* env vars at import time)
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI   # Google Gemini LLM wrapper
from langchain import hub                                    # Pull prompts from LangChain Hub
from langchain.agents import create_react_agent, AgentExecutor  # ReAct agent builder

# Import the four custom tools defined in tools.py
from tools import (
    get_race_situation,
    get_tyre_degradation,
    calculate_pit_window,
    search_f1_data,
)

# ---------------------------------------------------------------------------
# LLM setup — Google Gemini 2.5 Flash via langchain-google-genai
# temperature=0 ensures deterministic, factual outputs (no creative hallucinating)
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",   # Use the fast, capable Gemini 2.5 Flash model
    temperature=0,              # 0 = most deterministic; ideal for engineering decisions
    google_api_key=os.getenv("GOOGLE_API_KEY"),  # Key loaded from .env
)

# ---------------------------------------------------------------------------
# Tool list — all tools the agent can call
# The agent will decide which tool to invoke based on the user's question
# ---------------------------------------------------------------------------
tools = [
    get_race_situation,
    get_tyre_degradation,
    calculate_pit_window,
    search_f1_data,
]

# ---------------------------------------------------------------------------
# ReAct prompt — pulled from LangChain Hub
# "hwchase17/react" is the standard ReAct (Reasoning + Acting) prompt template
# It tells the LLM to think step-by-step, call tools, observe results, repeat
# ---------------------------------------------------------------------------
prompt = hub.pull("hwchase17/react")

# ---------------------------------------------------------------------------
# Agent construction
# create_react_agent wires the LLM + tools + prompt into a Runnable chain
# ---------------------------------------------------------------------------
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

# ---------------------------------------------------------------------------
# AgentExecutor — the runtime loop that calls the agent repeatedly until done
# verbose=True  : prints each Thought / Action / Observation step to stdout
# max_iterations: safety cap to prevent infinite loops (e.g. if LLM loops)
# handle_parsing_errors: if Gemini output is malformed, retry instead of crash
# ---------------------------------------------------------------------------
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,             # Show reasoning steps in terminal (great for debugging)
    max_iterations=6,         # Stop after 6 reasoning steps maximum
    handle_parsing_errors=True,  # Gracefully recover from LLM output format errors
)

# ---------------------------------------------------------------------------
# Adrian's personality prompt — prepended to every user query
# This shapes HOW the agent responds: short, precise, data-driven F1 comms style
# ---------------------------------------------------------------------------
PERSONALITY = (
    "You are Adrian, a calm and data-driven F1 race engineer with 15 years experience. "
    "You always justify strategy calls with numbers. "
    "You speak in short, precise sentences like real F1 radio comms."
)


def run_agent(user_input: str) -> str:
    """
    Main entry point: takes a user question, prepends Adrian's personality,
    runs the ReAct agent, and returns the final answer string.

    Args:
        user_input: The race strategy question from the user.

    Returns:
        The agent's strategy recommendation as a plain string.
    """
    # Combine personality + user question into a single prompt
    full_input = f"{PERSONALITY}\n\nUser question: {user_input}"

    # Invoke the agent executor; it returns a dict with key 'output'
    result = agent_executor.invoke({"input": full_input})

    # Extract the final text answer from the result dict
    return result.get("output", "No response generated.")


# ---------------------------------------------------------------------------
# Terminal mode — runs when the script is executed directly: python agent.py
# Allows you to test the agent without needing Telegram
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\U0001f3ce\ufe0f  F1 Race Strategy Agent — Terminal Mode")
    print("Type your race situation and press Enter. Type 'quit' to exit.\n")

    while True:
        # Read user input from the terminal
        user_input = input("You: ").strip()

        # Allow the user to exit gracefully
        if user_input.lower() in ("quit", "exit", "q"):
            print("Box box. Session over. \U0001f3c1")
            break

        # Skip empty input
        if not user_input:
            continue

        # Run the agent and print the result
        print("\nAdrian: ", end="", flush=True)
        response = run_agent(user_input)
        print(response)
        print()  # Blank line for readability
