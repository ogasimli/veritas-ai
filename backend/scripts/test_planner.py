import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.agents import get_adk_runner, create_planner_agent
from app.config import get_settings
from google.genai import types

SAMPLE_TEXT = """
Consolidated Statement of Profit or Loss
For the year ended 31 December 2023

Item                            2023 (USD)    2022 (USD)
--------------------------------------------------------
Revenue                         1,500,000     1,200,000
Cost of sales                   (800,000)     (700,000)
Gross profit                      700,000       500,000

Note 4: Trade receivables
As of 31 December 2023, trade receivables were 450,000 USD, 
compared to 380,000 USD in 2022.
"""

async def test_planner():
    print("Testing Planner Agent...")
    
    settings = get_settings()
    if not settings.google_api_key:
        print("Error: GOOGLE_API_KEY not found in settings.")
        print("Please ensure it is set in your .env file as GOOGLE_API_KEY=your_key")
        return

    try:
        # Create agent
        agent = create_planner_agent()
        print(f"Created agent: {agent.name} with model: {agent.model}")

        # Initialize runner with agent
        runner = await get_adk_runner(agent=agent)

        # Create message content
        message = types.Content(
            role="user",
            parts=[types.Part(text=SAMPLE_TEXT)]
        )

        # Run the agent (returns a generator)
        print("\n--- Running agent ---")
        final_result = None
        for event in runner.run(
            new_message=message,
            user_id="test-user"
        ):
            # Print events as they come in
            print(f"Event: {event.type if hasattr(event, 'type') else type(event).__name__}")
            final_result = event

        print("\n--- Findings (FSLIs) ---")
        if final_result and hasattr(final_result, 'state') and "fslis" in final_result.state:
            fslis = final_result.state["fslis"]
            for fsli in fslis:
                print(f"FSLI: {fsli.name}")
                print(f"  Source: {fsli.source_ref}")
                for val in fsli.values:
                    print(f"    - {val.label}: {val.amount} {val.unit}")
        else:
            print("No FSLIs found in state.")
            if final_result and hasattr(final_result, 'state'):
                print("Full state:", final_result.state)
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_planner())
