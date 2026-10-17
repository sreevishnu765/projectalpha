# breakpoint definition
breakpoints = [(0, 30, 0, 50, "Good"), (30.1, 60, 51, 100, "Satisfactory"), (60.1, 90, 101, 200, "Moderate"), (90.1, 120, 201, 300, "Poor"), (120.1, 250, 301, 400, "Very Poor"), (250.1, 380, 401, 500, "Severe"),]

#function for conversion
def pm25_to_aqi(concentration):
    for BP_low, BP_high, AQI_low, AQI_high, category in breakpoints:
        if concentration >= 0 and concentration <= BP_high:
            aqi = ((AQI_high - AQI_low) / (BP_high - BP_low)) * (concentration - BP_low) + AQI_low
            return round(aqi), category, None

    if concentration > 380:
        return 500, "Severe", "Unusually high reading detected — value exceeds standard AQI scale"

    return None, "Invalid", "Concentration value out of expected range"

# inverse of pm25_to_aqi
def aqi_to_pm25(index):
    if index is None or index < 0 or index > 500:
        return None
    for BP_low, BP_high, AQI_low, AQI_high, category in breakpoints:
        if index <= AQI_high:
            if index < AQI_low:
                return BP_low
            return (index - AQI_low) * (BP_high - BP_low) / (AQI_high - AQI_low) + BP_low
    return None

#advisory layer messages
advisory_messages = {
    "Good": {
        "general": "Air quality is good. Enjoy outdoor activities freely.",
        "sensitive": "Air quality is good. No precautions needed."
    },
    "Satisfactory": {
        "general": "Air quality is satisfactory. Outdoor activities are safe.",
        "sensitive": "Minor breathing discomfort possible. Monitor symptoms if sensitive to air pollution."
    },
    "Moderate": {
        "general": "Air quality is moderate. Prolonged outdoor exertion may cause mild discomfort.",
        "sensitive": "Limit prolonged outdoor exertion, especially if you have asthma, heart, or lung conditions."
    },
    "Poor": {
        "general": "Prolonged outdoor exposure may cause breathing discomfort. Limit extended outdoor activity.",
        "sensitive": "Avoid prolonged outdoor exertion. Consider wearing a mask outdoors and keep medication accessible."
    },
    "Very Poor": {
        "general": "Air quality is very poor. Reduce outdoor activity, especially strenuous exercise.",
        "sensitive": "Avoid outdoor activity where possible. Stay indoors, use an air purifier if available, and monitor symptoms closely."
    },
    "Severe": {
        "general": "Air quality is severe. Avoid outdoor activity and keep windows closed.",
        "sensitive": "Stay indoors at all times if possible. Seek medical attention immediately if experiencing breathing difficulty."
    }
}

def get_advisory(category, sensitivity_tier):
    if category not in advisory_messages:
        return "Unable to generate advisory: AQI category unavailable or invalid."

    if sensitivity_tier not in ("general", "sensitive"):
        return "Invalid sensitivity tier specified."

    return advisory_messages[category][sensitivity_tier]
