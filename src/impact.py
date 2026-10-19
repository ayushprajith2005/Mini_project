"""
Impact Estimation Layer for RainXplain.
Joins matched weather station region/state with static Indian population density data
to estimate potential infrastructure and population vulnerability impact.
"""

# Coarse State / District Population Density (people per sq km) based on Census / Official Data
POPULATION_DENSITY_MAP = {
    "Delhi": 11320,
    "Chandigarh": 9250,
    "Puducherry": 2547,
    "Daman & Diu": 2191,
    "Lakshadweep": 2149,
    "Bihar": 1106,
    "West Bengal": 1028,
    "Kerala": 860,
    "Uttar Pradesh": 829,
    "Haryana": 573,
    "Tamil Nadu": 555,
    "Punjab": 551,
    "Jharkhand": 414,
    "Assam": 398,
    "Goa": 394,
    "Maharashtra": 365,
    "Tripura": 350,
    "Karnataka": 319,
    "Gujarat": 308,
    "Andhra Pradesh": 308,
    "Telangana": 312,
    "Odisha": 270,
    "Madhya Pradesh": 236,
    "Rajasthan": 200,
    "Uttarakhand": 189,
    "Chhattisgarh": 189,
    "Meghalaya": 132,
    "Himachal Pradesh": 123,
    "Manipur": 115,
    "Nagaland": 119,
    "Sikkim": 86,
    "Mizoram": 52,
    "Arunachal Pradesh": 17,
    "Andaman & Nicobar Islands": 46,
    "Jammu & Kashmir": 124,
    "Ladakh": 5
}

def estimate_impact(state_name: str, risk_level: str, probability: float) -> dict:
    """
    Computes static vulnerability impact indicator given matched state and rain risk level.
    """
    density = POPULATION_DENSITY_MAP.get(state_name, 350)
    
    if density >= 800:
        density_category = "VERY HIGH DENSITY URBAN"
        density_badge = "#DC2626"
    elif density >= 400:
        density_category = "HIGH DENSITY REGION"
        density_badge = "#EA580C"
    elif density >= 150:
        density_category = "MODERATE DENSITY"
        density_badge = "#EAB308"
    else:
        density_category = "SPARSELY POPULATED"
        density_badge = "#16A34A"

    is_heavy = probability >= 0.35 or "HEAVY" in risk_level.upper()

    if is_heavy and density >= 600:
        overall_impact = "CRITICAL INFRASTRUCTURE & URBAN FLOOD RISK"
        impact_color = "#DC2626"
        recommendation = "High alert for municipal storm drainage, transit disruptions, and power grid protection."
    elif is_heavy and density >= 200:
        overall_impact = "ELEVATED REGIONAL IMPACT RISK"
        impact_color = "#EA580C"
        recommendation = "Monitor low-lying transport corridors and agricultural infrastructure."
    elif is_heavy:
        overall_impact = "MODERATE LOCALIZED RISK"
        impact_color = "#EAB308"
        recommendation = "Standard heavy rainfall protocol for rural/mountainous terrain."
    else:
        overall_impact = "LOW IMPACT POTENTIAL"
        impact_color = "#16A34A"
        recommendation = "Routine monitoring; no severe population impact anticipated."

    return {
        "state": state_name,
        "population_density_sq_km": density,
        "density_category": density_category,
        "overall_impact_label": overall_impact,
        "impact_color": impact_color,
        "recommendation": recommendation
    }
