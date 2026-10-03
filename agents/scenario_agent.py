"""
Scenario Agent - Phase 4
Interviews user about consumption scenario changes (electric vehicle, heat pump, solar panels, etc.)
"""

import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScenarioAgent:
    """Interviews user about consumption scenarios and validates inputs"""

    SCENARIOS = {
        "electric_vehicle": {
            "name": "Electric Vehicle",
            "questions": [
                {
                    "key": "annual_km",
                    "question": "How many kilometers per year will you drive?",
                    "default": 12000,
                    "unit": "km/year"
                },
                {
                    "key": "consumption_kwh_per_100km",
                    "question": "What's the vehicle's consumption in kWh per 100 km?",
                    "default": 17,
                    "unit": "kWh/100km"
                },
                {
                    "key": "charging_hours",
                    "question": "What time do you typically charge? (e.g., '20:00-08:00' for night charging, '09:00-17:00' for day)",
                    "default": "20:00-08:00",
                    "unit": "time range"
                }
            ]
        },
        "heat_pump": {
            "name": "Heat Pump",
            "questions": [
                {
                    "key": "annual_heating_kwh",
                    "question": "What's your annual heating consumption in kWh?",
                    "default": 4000,
                    "unit": "kWh/year"
                },
                {
                    "key": "heating_months",
                    "question": "Which months do you heat? (e.g., '10,11,12,1,2,3,4' for Oct-Apr)",
                    "default": "10,11,12,1,2,3,4",
                    "unit": "months"
                }
            ]
        },
        "solar_panels": {
            "name": "Solar Panels",
            "questions": [
                {
                    "key": "annual_production_kwh",
                    "question": "What's the expected annual solar production in kWh?",
                    "default": 3000,
                    "unit": "kWh/year"
                },
                {
                    "key": "peak_hours",
                    "question": "Peak production hours? (e.g., '08:00-16:00')",
                    "default": "08:00-16:00",
                    "unit": "time range"
                }
            ]
        },
        "remote_work": {
            "name": "Remote Work / Telework",
            "questions": [
                {
                    "key": "additional_consumption_percent",
                    "question": "Additional consumption percentage from home devices?",
                    "default": 15,
                    "unit": "%"
                },
                {
                    "key": "working_days_per_week",
                    "question": "How many days per week working from home?",
                    "default": 5,
                    "unit": "days"
                }
            ]
        }
    }

    def __init__(self):
        self.scenarios = self.SCENARIOS

    def get_available_scenarios(self) -> List[Dict]:
        """Return list of available scenarios"""
        return [
            {
                "id": key,
                "name": config["name"],
                "question_count": len(config["questions"])
            }
            for key, config in self.scenarios.items()
        ]

    def get_scenario_questions(self, scenario_id: str) -> Dict:
        """Get questions for a specific scenario"""
        if scenario_id not in self.scenarios:
            return {"error": f"Scenario '{scenario_id}' not found"}

        scenario = self.scenarios[scenario_id]
        return {
            "scenario_id": scenario_id,
            "name": scenario["name"],
            "questions": scenario["questions"]
        }

    def validate_scenario_input(self, scenario_id: str, answers: Dict) -> Dict:
        """Validate user answers for a scenario"""
        if scenario_id not in self.scenarios:
            return {"valid": False, "error": f"Scenario '{scenario_id}' not found"}

        scenario = self.scenarios[scenario_id]
        errors = []

        # Validate each question
        for q in scenario["questions"]:
            key = q["key"]
            if key not in answers:
                errors.append(f"Missing answer for: {q['question']}")
                continue

            value = answers[key]

            # Basic validation based on scenario type
            if scenario_id == "electric_vehicle":
                if key == "annual_km":
                    if not isinstance(value, (int, float)) or value < 0 or value > 100000:
                        errors.append(f"annual_km must be between 0 and 100,000")
                elif key == "consumption_kwh_per_100km":
                    if not isinstance(value, (int, float)) or value < 5 or value > 50:
                        errors.append(f"consumption_kwh_per_100km must be between 5 and 50")

            elif scenario_id == "heat_pump":
                if key == "annual_heating_kwh":
                    if not isinstance(value, (int, float)) or value < 0 or value > 20000:
                        errors.append(f"annual_heating_kwh must be between 0 and 20,000")

            elif scenario_id == "solar_panels":
                if key == "annual_production_kwh":
                    if not isinstance(value, (int, float)) or value < 0 or value > 50000:
                        errors.append(f"annual_production_kwh must be between 0 and 50,000")

            elif scenario_id == "remote_work":
                if key == "additional_consumption_percent":
                    if not isinstance(value, (int, float)) or value < 0 or value > 100:
                        errors.append(f"additional_consumption_percent must be between 0 and 100")

        if errors:
            return {"valid": False, "errors": errors}

        return {
            "valid": True,
            "scenario_id": scenario_id,
            "scenario_name": scenario["name"],
            "answers": answers
        }

    def generate_scenario_summary(self, scenario_id: str, answers: Dict) -> str:
        """Generate human-readable summary of scenario"""
        if scenario_id == "electric_vehicle":
            annual_kwh = (answers["annual_km"] / 100) * answers["consumption_kwh_per_100km"]
            return (
                f"Electric vehicle: {answers['annual_km']:,.0f} km/year "
                f"({answers['consumption_kwh_per_100km']} kWh/100km) = "
                f"{annual_kwh:,.0f} kWh/year, charged {answers['charging_hours']}"
            )
        elif scenario_id == "heat_pump":
            return (
                f"Heat pump: {answers['annual_heating_kwh']:,.0f} kWh/year "
                f"(months: {answers['heating_months']})"
            )
        elif scenario_id == "solar_panels":
            return (
                f"Solar panels: {answers['annual_production_kwh']:,.0f} kWh/year, "
                f"peak hours {answers['peak_hours']}"
            )
        elif scenario_id == "remote_work":
            return (
                f"Remote work: +{answers['additional_consumption_percent']}% consumption, "
                f"{answers['working_days_per_week']} days/week"
            )
        return "Unknown scenario"

    def generate_combined_summary(self, scenarios_with_answers: List[Dict]) -> str:
        """Generate summary for combined scenarios"""
        summaries = []
        total_additional_kwh = 0

        for scenario_data in scenarios_with_answers:
            scenario_id = scenario_data['scenario_id']
            answers = scenario_data['answers']
            summary = self.generate_scenario_summary(scenario_id, answers)
            summaries.append(summary)

        return " + ".join(summaries)
