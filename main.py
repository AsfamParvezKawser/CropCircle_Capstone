# main.py
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from tools import tools

load_dotenv()

# 1. DEFINE THE ORCHESTRATOR (Day 1 & 3: System Prompt = Skill Manifest)
orchestrator = LlmAgent(
    name="CropCircle_Agronomist",
    model="gemini-1.5-pro-latest", # Or gemini-1.5-flash for speed
    description="Master Agronomist Agent. Delegates to specialized Skills (Tools) for Soil, Weather, Market, Regs. Never guesses numbers.",
    instruction="""
    YOU ARE CROPCIRCLE. A precision agronomy swarm orchestrator.
    FARMERS ASK SHORT QUESTIONS. YOU MUST CALL TOOLS TO GET REAL DATA.
    
    WORKFLOW:
    1. IDENTIFY FIELD ID (Default: Field_7).
    2. IF NITROGEN/FERTILIZER QUESTION -> CALL `skill_n_calculator`.
    3. IF PEST/WEED/YELLOW QUESTION -> CALL `skill_pest_scout` with user description.
    4. IF MARKET/PRICE/SELL QUESTION -> CALL `skill_market_hedge`.
    5. SYNTHESIZE: Combine tool outputs into ONE actionable paragraph.
    6. FORMAT: **Recommendation** -> **Why (Data)** -> **Cost/ROI** -> **Compliance** -> **Next Step**.
    
    NEVER HALLUCINATE RATES. ALWAYS USE TOOLS.
    """,
    tools=tools,
)

# 2. RUNNER SETUP (For Local CLI / Streamlit)
session_service = InMemorySessionService()
runner = Runner(agent=orchestrator, app_name="CropCircle", session_service=session_service)

# 3. HELPER FOR STREAMLIT/CLI
async def run_agent(user_id: str, session_id: str, message: str) -> str:
    session = await session_service.get_session(app_name="CropCircle", user_id=user_id, session_id=session_id)
    if not session:
        session = await session_service.create_session(app_name="CropCircle", user_id=user_id, session_id=session_id)
    
    content = types.Content(role='user', parts=[types.Part(text=message)])
    final_response = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
    return final_response

# 4. CLI TEST (Run: python main.py)
if __name__ == "__main__":
    import asyncio
    async def test():
        print("🌾 CropCircle CLI Test. Type 'exit' to quit.")
        uid, sid = "farmer_joe", "session_1"
        while True:
            q = input("\nFarmer: ")
            if q.lower() == 'exit': break
            ans = await run_agent(uid, sid, q)
            print(f"\nCropCircle:\n{ans}")
    asyncio.run(test())
