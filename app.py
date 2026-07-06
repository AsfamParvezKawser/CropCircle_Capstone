# app.py
import streamlit as st
import asyncio
from main import run_agent

st.set_page_config(page_title="CropCircle 🌾", page_icon="🌾", layout="wide")

st.title("🌾 CropCircle: Your AI Agronomy Swarm")
st.caption("Powered by Google ADK + Gemini 1.5 Pro | Multi-Agent Skills: Soil, Weather, Market, Regs")

# Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = "demo_session_1"
if "user_id" not in st.session_state:
    st.session_state.user_id = "farmer_demo"
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Morning! Ask me about Field 7. Try: **'Should I top-dress wheat today?**' or **'Wheat looks yellow, what is it?'**"}]

# Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
if prompt := st.chat_input("Ask about Nitrogen, Pests, Markets, Weather..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("🤖 Orchestrator delegating to Soil, Weather, Market, Reg Agents..."):
            try:
                response = asyncio.run(run_agent(st.session_state.user_id, st.session_state.session_id, prompt))
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                err = f"Error: {e}. Check terminal for API Key/Quota."
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

# Sidebar - Context
with st.sidebar:
    st.header("🧠 Agent Architecture")
    st.markdown("""
    **Orchestrator:** `CropCircle_Agronomist` (Gemini 1.5 Pro)
    
    **Skills (Tools):**
    1. `skill_n_calculator` → SoilMCP + WeatherMCP + MarketMCP + RegMCP
    2. `skill_pest_scout` → Vision Mock
    3. `skill_market_hedge` → MarketMCP
    
    **Data Sources (Mocked for Demo):**
    *   Soil: `data/soil_field7.json`
    *   Weather: Open-Meteo (Live Free API)
    *   Market: `data/market_prices.json`
    *   Regs: `data/regulations_mn.json`
    """)
    st.divider()
    st.markdown("**Eval Trajectories:** `eval/golden_trajectories.yaml`")
    st.markdown("**Spec (SDD):** `specs/nitrogen_recommendation.feature`")
