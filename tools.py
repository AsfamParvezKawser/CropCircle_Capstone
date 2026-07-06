# tools.py
import json, os, requests, datetime
from typing import Dict, Any, List
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

# --- PYDANTIC MODELS (Structured Outputs) ---
class NRecommendation(BaseModel):
    rate_lbs_ac: float = Field(description="Recommended Nitrogen rate lbs/acre")
    timing: str = Field(description="Specific timing window e.g. 'Tuesday 6-10 AM'")
    total_cost_usd_ac: float
    roi_estimate: float
    compliance_notes: List[str]
    citation: str

class WeatherForecast(BaseModel):
    precipitation_in_7day: float
    max_temp_f: float
    min_temp_f: float
    spray_window_hours: List[str] # e.g. ["Tue 06:00-10:00", "Wed 06:00-10:00"]

# --- MOCK MCP SERVERS (Python Classes) ---
class SoilMCP:
    def __init__(self): self.path = "data/soil_field7.json"
    def get_profile(self, field_id: str) -> Dict:
        with open(self.path) as f: return json.load(f)

class MarketMCP:
    def __init__(self): self.path = "data/market_prices.json"
    def get_prices(self) -> Dict:
        with open(self.path) as f: return json.load(f)

class RegMCP:
    def __init__(self): self.path = "data/regulations_mn.json"
    def get_rules(self, state: str) -> Dict:
        with open(self.path) as f: return json.load(f)

class WeatherMCP:
    # Uses FREE Open-Meteo (No Key)
    def get_forecast(self, lat: float=44.9, lon: float=-93.1) -> WeatherForecast:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat, "longitude": lon,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "hourly": "windspeed_10m,precipitation_probability",
            "timezone": "America/Chicago", "forecast_days": 7
        }
        try:
            r = requests.get(url, params=params, timeout=10).json()
            # Simplified parsing for demo
            precip = sum(r['daily']['precipitation_sum']) * 0.0393701 # mm to inches
            spray_windows = []
            for i in range(len(r['hourly']['time'])):
                dt = datetime.datetime.fromisoformat(r['hourly']['time'][i])
                wind = r['hourly']['windspeed_10m'][i]
                rain_prob = r['hourly']['precipitation_probability'][i]
                if 6 <= dt.hour <= 10 and wind < 10 and rain_prob < 20:
                    spray_windows.append(dt.strftime("%a %H:%M"))
            return WeatherForecast(
                precipitation_in_7day=round(precip, 2),
                max_temp_f=max(r['daily']['temperature_2m_max']) * 9/5 + 32,
                min_temp_f=min(r['daily']['temperature_2m_min']) * 9/5 + 32,
                spray_window_hours=spray_windows[:3]
            )
        except Exception as e:
            print(f"Weather API Error: {e}")
            return WeatherForecast(precipitation_in_7day=0.5, max_temp_f=75, min_temp_f=55, spray_window_hours=["Tue 06:00", "Wed 06:00"])

# --- AGENT SKILLS (Day 3 Concept) ---
# Each function is a "Skill". Docstring = Prompt Engineering.

def skill_n_calculator(field_id: str) -> NRecommendation:
    """
    SKILL: Calculate Variable Rate Nitrogen Recommendation (UMN/Stanford Logic).
    INPUT: field_id (str). 
    TOOLS: SoilMCP, MarketMCP, WeatherMCP, RegMCP.
    OUTPUT: NRecommendation JSON.
    """
    soil = SoilMCP().get_profile(field_id)
    market = MarketMCP().get_prices()
    weather = WeatherMCP().get_forecast()
    regs = RegMCP().get_rules("MN")

    # 1. Agronomic Calc (Simplified UMN Equation)
    # N_Rec = (Yield_Goal * 2.0) - Soil_Nitrate_Credit - Prev_Crop_Credit - OM_Credit
    yield_goal = soil['yield_goal_bu_ac']
    nitrate_credit = soil['last_soil_test']['nitrate_ppm'] * 0.3 * 12 # ppm * depth factor approx
    prev_crop_credit = 40 if soil['previous_crop'] == 'Soybean' else 0
    om_credit = soil['last_soil_test']['om_pct'] * 20
    
    raw_rec = (yield_goal * 2.0) - nitrate_credit - prev_crop_credit - om_credit
    raw_rec = max(0, raw_rec)

    # 2. Economic Optimization (Max Profit)
    # Cost per lb N = Urea_Price / 2000 * (1/0.46) 
    n_cost_lb = (market['urea_price_usd_ton'] / 2000) / 0.46
    # Value per bu wheat
    wheat_val = market['local_elevator_bid_usd_bu']
    # Marginal yield response ~ 0.05 bu/lb N near optimum (simplified)
    # Optimal where Marginal Cost = Marginal Revenue -> n_cost_lb = wheat_val * 0.05
    # This is complex, so we clamp raw_rec to economic optimum ~1.2x cost ratio
    econ_opt = min(raw_rec, 100) # Cap for demo safety

    # 3. Compliance Check
    max_allowed = regs['max_n_rate_lbs_ac_wheat']
    final_rate = min(econ_opt, max_allowed)
    compliance = []
    if final_rate == max_allowed: compliance.append(f"CAPPED at MN Max Rate ({max_allowed} lbs/ac).")
    if regs['fall_application_ban'] and datetime.datetime.now().month > 9: compliance.append("FALL APPLICATION BAN ACTIVE.")
    compliance.append(f"Setback: {regs['setback_ft_water']}ft from water.")

    # 4. Timing from Weather
    timing = "Immediate" if weather.spray_window_hours else "Wait for Wind < 10mph / No Rain"
    if weather.spray_window_hours: timing = f"BEST: {weather.spray_window_hours[0]} (Low Wind/Dry)"

    # 5. Economics
    cost = (final_rate * n_cost_lb) + market['application_cost_usd_ac']
    # Rough ROI: (Yield Increase * Price) / Cost. Yield Inc ~ final_rate * 0.05
    yield_inc = final_rate * 0.05
    revenue = yield_inc * wheat_val
    roi = revenue / cost if cost > 0 else 0

    return NRecommendation(
        rate_lbs_ac=round(final_rate, 1),
        timing=timing,
        total_cost_usd_ac=round(cost, 2),
        roi_estimate=round(roi, 2),
        compliance_notes=compliance,
        citation="UMN Extension 0855 / MN NMP Rules"
    )

def skill_pest_scout(field_id: str, image_description: str) -> Dict:
    """
    SKILL: Pest/Weed Identification from Farmer Description (Mock CV).
    Returns structured action plan.
    """
    # Mock Logic - In real life: Vertex Vision API call here
    pests = {"yellow": "Nitrogen Deficiency / Yellow Rust", "holes": "Armyworm", "weeds": "Wild Oats / Kochia"}
    found = [v for k, v in pests.items() if k in image_description.lower()]
    return {"field": field_id, "observation": image_description, "detected_issues": found or ["Healthy - No visible stress"], "action": "Tissue test recommended for Yellow." if "yellow" in image_description.lower() else "Scout again in 3 days."}

def skill_market_hedge(crop: str, bushels: int) -> Dict:
    """SKILL: Simple Grain Marketing Advice."""
    m = MarketMCP().get_prices()
    basis = m['local_elevator_bid_usd_bu'] - m['cbots_wheat_usd_bu']
    return {
        "current_basis": round(basis, 2),
        "advice": "Basis weak. Consider storing if storage cost < $0.05/bu/mo." if basis < -0.20 else "Basis strong. Price 30% of expected yield.",
        "futures_price": m['cbots_wheat_usd_bu'],
        "cash_price": m['local_elevator_bid_usd_bu']
    }

# --- EXPORT TOOLS FOR ADK ---
# Wrap functions with FunctionTool so ADK sees them
tools = [
    FunctionTool(skill_n_calculator),
    FunctionTool(skill_pest_scout),
    FunctionTool(skill_market_hedge),
]
