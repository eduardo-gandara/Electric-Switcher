"""
Advisor Analyzer - Phase 3
Análisis de sensibilidad a consumo, riesgos y recomendaciones
"""

import logging
from typing import List, Dict, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SensitivityAnalyzer:
    """Analiza cómo cambia el costo con variaciones de consumo (±20%)"""

    def __init__(self, base_consumption_kwh: float):
        self.base_consumption = base_consumption_kwh
        self.low_consumption = base_consumption_kwh * 0.8  # -20%
        self.high_consumption = base_consumption_kwh * 1.2  # +20%

    def scale_monthly_costs(self, base_monthly_costs: List[float]) -> Dict[str, List[float]]:
        """
        Escala costos mensuales según variación de consumo.

        Args:
            base_monthly_costs: Lista de 24 costos mensuales (en EUR)

        Returns:
            Dict con costos para -20%, 0%, +20% de consumo
        """
        # Separar componentes fijos y variables
        # Asumimos que ~70% es variable (consumo) y 30% es fijo (standing charge, PSO)
        # Esta es una aproximación razonable para Irlanda

        costs = {
            "low_20": [],
            "base": base_monthly_costs,
            "high_20": []
        }

        for monthly_cost in base_monthly_costs:
            # Asumir 70% variable, 30% fijo
            variable = monthly_cost * 0.7
            fixed = monthly_cost * 0.3

            # Escalar variable según consumo
            low_variable = variable * 0.8
            high_variable = variable * 1.2

            costs["low_20"].append(round(fixed + low_variable, 2))
            costs["high_20"].append(round(fixed + high_variable, 2))

        return costs

    def get_sensitivity_summary(self, base_costs: Dict[str, List[float]]) -> Dict:
        """Resumen: costo anual a -20%, base, +20%"""
        return {
            "low_20_annual": round(sum(base_costs["low_20"]), 2),
            "base_annual": round(sum(base_costs["base"]), 2),
            "high_20_annual": round(sum(base_costs["high_20"]), 2),
            "variance": round(
                sum(base_costs["high_20"]) - sum(base_costs["low_20"]), 2
            )  # Rango total
        }


class RiskAnalyzer:
    """Identifica riesgos en cada tarifa"""

    @staticmethod
    def analyze_tariff_risks(tariff: Dict) -> Dict:
        """
        Analiza riesgos de una tarifa.

        Retorna:
        {
            "risks": [{"level": "high/medium/low", "description": "..."}],
            "summary": "Texto corto de riesgo"
        }
        """
        risks = []

        # 1. Descuentos que vencen
        discount = tariff.get("discount", {})
        if discount.get("percent", 0) > 25:
            months = discount.get("months", 12)
            if months == 12:
                risks.append({
                    "level": "medium",
                    "icon": "⏰",
                    "title": "Descuento temporal",
                    "description": f"Descuento del {discount.get('percent', 0):.0f}% vence después de 12 meses"
                })

        # 2. Tarifa variable (rates no son iguales en día/noche = volatilidad)
        unit_rates = tariff.get("unit_rates_c_per_kwh_ex_vat", {})
        rates = [unit_rates.get("day", 0), unit_rates.get("night", 0), unit_rates.get("peak", 0)]
        rates = [r for r in rates if r]  # Filtrar nulls

        if len(rates) > 1:
            rate_variance = max(rates) - min(rates)
            if rate_variance > 10:  # Varianza alta
                risks.append({
                    "level": "medium",
                    "icon": "📊",
                    "title": "Variabilidad horaria",
                    "description": f"Diferencia entre franjas horarias: {rate_variance:.1f} c/kWh"
                })

        # 3. Exit fee
        exit_fee = tariff.get("exit_fee_eur", 0)
        if exit_fee > 50:
            risks.append({
                "level": "medium",
                "icon": "🚪",
                "title": "Penalización por salida",
                "description": f"Cuota de cancelación: €{exit_fee:.0f}"
            })

        # 4. Condiciones (pago directo, facturación electrónica)
        conditions = tariff.get("conditions", [])
        if "direct_debit" in conditions:
            # No es realmente un riesgo, pero es una condición
            pass

        # 5. Cashback (si es muy bajo o nulo = sin incentivo inicial)
        cashback = tariff.get("cashback_eur", 0)
        if cashback < 25:
            risks.append({
                "level": "low",
                "icon": "💰",
                "title": "Sin incentivo inicial",
                "description": f"Cashback bajo o nulo: €{cashback:.0f}"
            })

        return {
            "risks": risks,
            "count": len(risks),
            "level": "high" if len(risks) >= 3 else "medium" if len(risks) == 2 else "low"
        }


class AdvisorRecommender:
    """Genera recomendaciones personalizadas"""

    @staticmethod
    def rank_tariffs(
        tariffs_with_costs: List[Dict]
    ) -> List[Dict]:
        """
        Ordena tarifas por mejor ahorro anual.

        Cada tariff_with_cost contiene:
        {
            "tariff": {...},
            "annual_cost": float,
            "monthly_costs": [...],
            "sensitivity": {...},
            "risks": {...}
        }
        """
        # Ordenar por costo anual (menor primero)
        ranked = sorted(tariffs_with_costs, key=lambda x: x["annual_cost"])

        # Agregar ranking y savings
        best_cost = ranked[0]["annual_cost"] if ranked else 0

        for idx, item in enumerate(ranked):
            item["rank"] = idx + 1
            item["annual_savings"] = round(item["annual_cost"] - best_cost, 2)
            item["savings_percent"] = round(
                ((item["annual_cost"] - best_cost) / best_cost * 100) if best_cost > 0 else 0, 1
            )

        return ranked

    @staticmethod
    def get_recommendation(ranked_tariffs: List[Dict]) -> Dict:
        """
        Generates final recommendation based on:
        - Best cost
        - Risk level
        - Sensitivity to changes
        """
        if not ranked_tariffs:
            return {
                "tariff_name": "N/A",
                "supplier": "N/A",
                "text": "No tariffs available for analysis.",
                "reasoning": []
            }

        best = ranked_tariffs[0]
        num_months = len(best.get('monthly_costs', []))

        reasoning = [
            f"Best total cost ({num_months} months): €{best['annual_cost']:.2f}"
        ]

        # Analizar sensibilidad
        sensitivity = best.get("sensitivity", {})
        variance = sensitivity.get("variance", 0)
        if variance < 100:
            reasoning.append(f"Estable ante cambios de consumo (rango: €{variance:.2f})")
        else:
            reasoning.append(f"Sensible a cambios de consumo (rango: €{variance:.2f})")

        # Analizar riesgos
        risks = best.get("risks", {})
        if risks.get("count", 0) == 0:
            reasoning.append("Sin riesgos identificados")
        elif risks.get("count", 0) <= 2:
            reasoning.append("Riesgos moderados identificados")
        else:
            reasoning.append("Varios riesgos a considerar")

        # Comparar con segundo mejor
        if len(ranked_tariffs) > 1:
            second = ranked_tariffs[1]
            savings = round(second["annual_cost"] - best["annual_cost"], 2)
            reasoning.append(f"Ahorra €{savings:.2f} vs. siguiente opción")

        recommendation_text = (
            f"We recommend **{best['tariff']['plan_name']}** from "
            f"**{best['tariff']['supplier']}**. "
            f"It's the most economical option over {num_months} months (€{best['annual_cost']:.2f}) "
            f"and offers a good balance between cost and stability. "
        )

        if risks.get("count", 0) > 0:
            recommendation_text += (
                f"Note: {risks.get('count')} risk(s) identified - review before switching."
            )

        return {
            "tariff_name": best["tariff"]["plan_name"],
            "supplier": best["tariff"]["supplier"],
            "annual_cost": best["annual_cost"],
            "rank": best.get("rank", 1),
            "text": recommendation_text,
            "reasoning": reasoning,
            "source_url": best["tariff"].get("source_url", "")
        }
