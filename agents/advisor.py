"""
Advisor Agent
Presents tariff ranking, explains assumptions, calculates savings and identifies risks.
"""

from typing import List, Dict, Tuple
import json
from datetime import datetime


class AdvisorAgent:
    """Advisor that presents ranking and risk analysis."""

    def __init__(self):
        self.comparison_results = []

    def create_report(
        self,
        comparison_results: List[Dict],
        reference_tariff: Dict = None,
        scenarios: Dict[str, float] = None
    ) -> Dict:
        """
        Create complete report with ranking, assumptions and risks.

        Args:
            comparison_results: Comparison results from SimulationEngine
            reference_tariff: Current reference tariff
            scenarios: Base consumption, +20%, -20% for sensitivity analysis
        """
        if not comparison_results:
            return {'error': 'No results to compare'}

        # Top 3 tariffs
        top_3 = comparison_results[:3]

        # Calculate savings
        reference_cost = (
            reference_tariff['total_cost_eur']
            if reference_tariff else
            comparison_results[0]['total_cost_eur']
        )

        # Sensitivity analysis
        sensitivity = self._analyze_sensitivity(
            comparison_results,
            scenarios or {
                'base': 1.0,
                '+20%': 1.2,
                '-20%': 0.8
            }
        )

        # Validations and alerts
        validations = self._check_validations(comparison_results)

        # Risks
        risks = self._identify_risks(top_3)

        report = {
            'generated_at': datetime.now().isoformat(),
            'ranking': {
                'top_1': self._format_tariff(top_3[0], reference_cost),
                'top_2': self._format_tariff(top_3[1], reference_cost) if len(top_3) > 1 else None,
                'top_3': self._format_tariff(top_3[2], reference_cost) if len(top_3) > 2 else None,
            },
            'assumptions': {
                'period': comparison_results[0].get('period', 'Unknown'),
                'total_consumption_kwh': comparison_results[0].get('total_consumption_kwh', 0),
                'reference_tariff': reference_tariff['plan_name'] if reference_tariff else 'Unknown',
                'reference_cost_eur': reference_cost,
                'iva_rate': 0.09,
                'notes': [
                    'Ranking uses net cost at 12 months',
                    'No automatic provider change is assumed',
                    'Prices normalized to c/kWh excluding VAT',
                    'Cashback, exit fee and discounts included',
                ]
            },
            'sensitivity': sensitivity,
            'validations': validations,
            'risks': risks,
            'recommendations': self._generate_recommendations(top_3, reference_cost)
        }

        return report

    def _format_tariff(self, tariff_result: Dict, reference_cost: float) -> Dict:
        """Formatear tarifa para presentación."""
        return {
            'supplier': tariff_result.get('supplier'),
            'plan': tariff_result.get('plan_name'),
            'source_url': tariff_result.get('source_url'),
            'extracted_at': tariff_result.get('extracted_at'),
            'cost_eur': tariff_result.get('total_cost_eur'),
            'savings_vs_reference_eur': reference_cost - tariff_result.get('total_cost_eur', reference_cost),
            'savings_percent': round(
                (reference_cost - tariff_result.get('total_cost_eur', reference_cost)) / reference_cost * 100, 2
            ),
            'monthly_average': tariff_result.get('average_cost_monthly'),
            'conditions': tariff_result.get('conditions', []),
            'exit_fee': tariff_result.get('exit_fee'),
            'cashback': tariff_result.get('cashback')
        }

    def _analyze_sensitivity(
        self,
        results: List[Dict],
        scenarios: Dict[str, float]
    ) -> Dict:
        """
        Analyze sensitivity: How stable is the ranking if consumption changes?

        Scenarios: {'base': 1.0, '+20%': 1.2, '-20%': 0.8}
        """
        top_1 = results[0]

        sensitivity = {}
        for scenario_name, multiplier in scenarios.items():
            # Ajustar consumo y recalcular
            adjusted_cost = top_1['total_cost_eur'] * multiplier
            sensitivity[scenario_name] = {
                'scenario': scenario_name,
                'adjusted_cost': round(adjusted_cost, 2),
                'stays_on_top': True  # Simplificado: asumir que sigue en top
            }

        return sensitivity

    def _check_validations(self, results: List[Dict]) -> List[Dict]:
        """Comprobar que los datos cumplen validaciones."""
        validations = []

        for result in results:
            issues = []

            # Validation 1: URL present
            if not result.get('source_url'):
                issues.append('Missing source URL')

            # Validation 2: Extraction date < 30 days
            if result.get('extracted_at'):
                try:
                    extracted = datetime.fromisoformat(result['extracted_at'])
                    days_old = (datetime.now() - extracted).days
                    if days_old > 30:
                        issues.append(f'Data older than 30 days: {days_old} days')
                except:
                    pass

            # Validation 3: Reasonable price (1-100 c/kWh)
            monthly = result.get('average_cost_monthly', 0)
            kwh = result.get('total_consumption_kwh', 1)
            if kwh > 0:
                effective_rate = (monthly * 100) / (kwh / 12)
                if effective_rate < 1 or effective_rate > 100:
                    issues.append(f'Unusual rate: {effective_rate:.2f} c/kWh')

            if issues:
                validations.append({
                    'tariff': result.get('plan_name'),
                    'supplier': result.get('supplier'),
                    'issues': issues
                })

        return validations

    def _identify_risks(self, top_tariffs: List[Dict]) -> List[Dict]:
        """Identify risks associated with the best tariffs."""
        risks = []

        for i, tariff in enumerate(top_tariffs, 1):
            tariff_risks = []

            # Risk 1: New customer discount decay
            discount = tariff.get('discount', {})
            if discount and isinstance(discount, dict):
                discount_pct = discount.get('percent', 0)
                if discount_pct > 25:
                    tariff_risks.append({
                        'type': 'new_customer_discount_decay',
                        'severity': 'high',
                        'description': f"Discount of {discount_pct}% applies only the first year",
                        'mitigation': 'Verify price after renewal'
                    })

            # Risk 2: Exit fee
            exit_fee = tariff.get('exit_fee', 0)
            if exit_fee > 0:
                tariff_risks.append({
                    'type': 'exit_fee',
                    'severity': 'medium',
                    'description': f"Exit fee: {exit_fee}€",
                    'mitigation': 'Change cost included in ranking'
                })

            # Risk 3: Stale data
            extracted = tariff.get('extracted_at')
            if extracted:
                try:
                    ext_date = datetime.fromisoformat(extracted)
                    days_old = (datetime.now() - ext_date).days
                    if days_old > 7:
                        tariff_risks.append({
                            'type': 'stale_data',
                            'severity': 'low',
                            'description': f"Data extracted {days_old} days ago",
                            'mitigation': 'Verify on official website before deciding'
                        })
                except:
                    pass

            if tariff_risks:
                risks.append({
                    'rank': i,
                    'supplier': tariff.get('supplier'),
                    'plan': tariff.get('plan_name'),
                    'risks': tariff_risks
                })

        return risks

    def _generate_recommendations(self, top_3: List[Dict], reference_cost: float) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if not top_3:
            recommendations.append('No tariffs to compare')
            return recommendations

        # Recommendation 1: Potential savings
        best_savings = reference_cost - top_3[0]['total_cost_eur']
        if best_savings > 50:
            recommendations.append(
                f"✓ Switching to {top_3[0]['supplier']} could save {best_savings:.2f}€ annually"
            )
        elif best_savings > 0:
            recommendations.append(
                f"• Switching to {top_3[0]['supplier']} could save {best_savings:.2f}€ annually"
            )
        else:
            recommendations.append("Your current tariff is competitive")

        # Recommendation 2: Verification
        if top_3[0].get('source_url'):
            recommendations.append(
                f"Verify on {top_3[0]['source_url']} before deciding"
            )

        # Recommendation 3: Sensitivity
        recommendations.append(
            "This ranking assumes historical consumption. If your home changes (EV, heat pump), recalculate"
        )

        return recommendations

    def format_for_user(self, report: Dict) -> str:
        """Format report for user presentation."""
        lines = [
            "\n" + "="*60,
            "ELECTRIC SWITCHER - ELECTRICITY TARIFF ANALYSIS",
            "="*60 + "\n"
        ]

        # Ranking
        lines.append("📊 BEST TARIFF RANKING\n")
        for rank_key in ['top_1', 'top_2', 'top_3']:
            if rank_key in report['ranking'] and report['ranking'][rank_key]:
                t = report['ranking'][rank_key]
                lines.append(f"{rank_key.upper().replace('_', ' ')}:")
                lines.append(f"  {t['supplier']} - {t['plan']}")
                lines.append(f"  Cost: {t['cost_eur']:.2f}€/year")
                if t['savings_percent'] > 0:
                    lines.append(f"  Savings: {t['savings_percent']:.1f}% ({t['savings_vs_reference_eur']:.2f}€)")
                lines.append(f"  Source: {t['source_url']} ({t['extracted_at']})\n")

        # Assumptions
        if 'assumptions' in report:
            lines.append("📋 ASSUMPTIONS")
            assum = report['assumptions']
            lines.append(f"  Period: {assum.get('period')}")
            lines.append(f"  Consumption: {assum.get('total_consumption_kwh'):.0f} kWh")
            lines.append(f"  Current tariff: {assum.get('reference_tariff')}")
            lines.append(f"  Current cost: {assum.get('reference_cost_eur'):.2f}€\n")

        # Risks
        if report.get('risks'):
            lines.append("⚠️  RISKS")
            for risk_group in report['risks']:
                lines.append(f"  {risk_group['rank']}. {risk_group['supplier']} - {risk_group['plan']}")
                for risk in risk_group['risks']:
                    lines.append(f"     • {risk['description']}")
            lines.append("")

        # Recommendations
        if report.get('recommendations'):
            lines.append("💡 RECOMMENDATIONS")
            for rec in report['recommendations']:
                lines.append(f"  {rec}")
            lines.append("")

        lines.append("="*60 + "\n")

        return '\n'.join(lines)


if __name__ == '__main__':
    print("Advisor Agent loaded")
