# 🌾 CropCircle – Multi-Agent Agronomy Swarm
**Google AI Agents Capstone | Agents for Good Track | Vibe Coded with ADK + Gemini 1.5 Pro**

[![Watch Demo](https://img.shields.io/badge/Video-Demo-red?logo=youtube)](YOUR_YOUTUBE_LINK_HERE)
[![Kaggle Writeup](https://img.shields.io/badge/Kaggle-Writeup-blue?logo=kaggle)](YOUR_KAGGLE_WRITEUP_URL_HERE)

## 🎯 The Problem
Farmers drown in dashboards but starve for **decisions**. They need: *"What do I do today?"* — not another map.

## 🤖 The Solution: An Agent Swarm
**CropCircle** is a **hierarchical multi-agent system** built on **Google ADK**. A single **Orchestrator** delegates to specialized **Skills (Tools)** that act as **Mock MCP Servers** for Soil, Live Weather, Markets, and Regulations.

```mermaid
graph LR
    User[Farmer: WhatsApp/Voice/PWA] --> Orch[Orchestrator Agent\nGemini 1.5 Pro]
    Orch -->|Tool Call| NCalc[Skill: N-Calculator\nSoil+Wx+Market+Reg]
    Orch -->|Tool Call| Pest[Skill: Pest Scout\nVision Mock]
    Orch -->|Tool Call| Mkt[Skill: Market Hedge\nBasis Logic]
