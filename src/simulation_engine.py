"""
Electric Switcher - Simulation Engine
Motor de simulación determinista de costos de tarifas eléctricas.
Aplica cada tarifa al perfil de consumo de 30 minutos y calcula el costo con IVA.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import json


@dataclass
class TariffRecord:
    """Registro de una tarifa eléctrica."""
    supplier: str
    plan_name: str
    source_url: str
    extracted_at: str
    contract_months: int
    unit_rates_c_per_kwh_ex_vat: Dict[str, float]  # {'day', 'night', 'peak'}
    bands: Dict[str, Tuple[str, str]]  # time windows for bands
    standing_charge_c_per_day: float
    pso_levy_eur_per_month: float
    discount: Optional[Dict[str, any]]  # {'percent', 'applies_to', 'months'}
    cashback_eur: float = 0.0
    exit_fee_eur: float = 0.0
    conditions: List[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'TariffRecord':
        """Crear desde diccionario JSON."""
        rates = data.get('unit_rates_c_per_kwh_ex_vat', {})
        rates = {k: (v or 0.0) for k, v in rates.items()}

        return cls(
            supplier=data.get('supplier'),
            plan_name=data.get('plan_name'),
            source_url=data.get('source_url'),
            extracted_at=data.get('extracted_at'),
            contract_months=data.get('contract_months', 12),
            unit_rates_c_per_kwh_ex_vat=rates,
            bands=data.get('bands', {}),
            standing_charge_c_per_day=data.get('standing_charge_c_per_day') or 0.0,
            pso_levy_eur_per_month=data.get('pso_levy_eur_per_month') or 0.0,
            discount=data.get('discount'),
            cashback_eur=data.get('cashback_eur') or 0.0,
            exit_fee_eur=data.get('exit_fee_eur') or 0.0,
            conditions=data.get('conditions', [])
        )


class ConsumptionProfile:
    """Perfil de consumo agregado por franja, mes y hora."""

    def __init__(self, df: pd.DataFrame):
        """
        df: DataFrame con columnas [timestamp, kwh, band]
        donde band ∈ {'day', 'night', 'peak'}
        """
        self.df = df.copy()
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self._aggregate()

    def _aggregate(self):
        """Agregar consumo por mes, banda y hora."""
        self.df['year_month'] = self.df['timestamp'].dt.to_period('M')
        self.df['hour'] = self.df['timestamp'].dt.hour

        self.monthly = self.df.groupby(['year_month', 'band'])['kwh'].sum()
        self.hourly = self.df.groupby(['year_month', 'hour', 'band'])['kwh'].sum()

    def get_kwh_by_band_month(self, year_month: str, band: str) -> float:
        """Obtener kWh por franja y mes."""
        try:
            return self.monthly.loc[(pd.Period(year_month, 'M'), band)]
        except KeyError:
            return 0.0

    def get_kwh_by_band_hour_month(self, year_month: str, hour: int, band: str) -> float:
        """Obtener kWh por franja, hora y mes."""
        try:
            return self.hourly.loc[(pd.Period(year_month, 'M'), hour, band)]
        except KeyError:
            return 0.0


class SimulationEngine:
    """Motor de simulación de costos de tarifa eléctrica."""

    IVA_RATE = 0.09  # 9%

    def __init__(self, consumption_profile: ConsumptionProfile, iva_rate: float = 0.09):
        self.profile = consumption_profile
        self.iva_rate = iva_rate

    def calculate_monthly_cost(
        self,
        tariff: TariffRecord,
        year_month: str,
        date_range_start: datetime = None,
        date_range_end: datetime = None
    ) -> Dict:
        """
        Calcular costo mensual para una tarifa.

        Retorna diccionario con desglose de componentes.
        """
        # Inicializar
        period = pd.Period(year_month, 'M')

        # Cálculo de consumo por banda
        consumption = {}
        for band in ['day', 'night', 'peak']:
            consumption[band] = self.profile.get_kwh_by_band_month(year_month, band)

        # Días en el mes (para cargo fijo)
        days_in_month = period.days_in_month

        # Precio de consumo sin IVA
        consumption_cost = 0.0
        for band, kwh in consumption.items():
            price_c_per_kwh = tariff.unit_rates_c_per_kwh_ex_vat.get(band, 0.0) or 0.0
            consumption_cost += kwh * price_c_per_kwh

        # Cargo fijo (standing charge)
        standing_charge = tariff.standing_charge_c_per_day * days_in_month

        # PSO levy
        pso_levy_eur = tariff.pso_levy_eur_per_month
        pso_levy_c = pso_levy_eur * 100  # convertir a céntimos

        # Subtotal sin IVA (en céntimos)
        subtotal_c = consumption_cost + standing_charge + pso_levy_c

        # Aplicar descuento si existe
        discount_percent = 0.0
        if tariff.discount:
            discount_percent = tariff.discount.get('percent', 0.0)
            applies_to = tariff.discount.get('applies_to', 'consumption')
            if applies_to == 'consumption':
                consumption_cost *= (1 - discount_percent / 100)
                subtotal_c = consumption_cost + standing_charge + pso_levy_c
            elif applies_to == 'all':
                subtotal_c *= (1 - discount_percent / 100)

        # IVA (9%)
        iva_amount_c = subtotal_c * self.iva_rate

        # Cashback
        cashback_c = tariff.cashback_eur * 100

        # Total (en céntimos)
        total_c = subtotal_c + iva_amount_c - cashback_c
        total_eur = total_c / 100

        return {
            'year_month': year_month,
            'consumption_kwh': sum(consumption.values()),
            'consumption_by_band': consumption,
            'consumption_cost_c': consumption_cost,
            'standing_charge_c': standing_charge,
            'pso_levy_c': pso_levy_c,
            'subtotal_c': subtotal_c,
            'discount_percent': discount_percent,
            'discount_amount_c': subtotal_c * discount_percent / 100 if discount_percent > 0 else 0,
            'iva_amount_c': iva_amount_c,
            'iva_rate': self.iva_rate,
            'cashback_c': cashback_c,
            'total_c': total_c,
            'total_eur': total_eur,
            'days_in_month': days_in_month
        }

    def calculate_annual_cost(
        self,
        tariff: TariffRecord,
        start_month: str,  # ej: '2026-06'
        end_month: str,    # ej: '2026-09'
        discount_changes: Optional[Dict[str, float]] = None  # {month: discount%}
    ) -> Dict:
        """
        Calcular costo anual para una tarifa.
        Soporta cambios de descuento a mitad del período.

        Args:
            tariff: Registro de tarifa
            start_month: Mes de inicio (YYYY-MM)
            end_month: Mes de fin (YYYY-MM)
            discount_changes: Cambios de descuento por mes
        """
        # Generar rango de meses
        start = pd.Period(start_month, 'M')
        end = pd.Period(end_month, 'M')
        months = pd.period_range(start, end, freq='M')

        monthly_costs = []
        total_cost = 0.0
        total_consumption = 0.0

        for month in months:
            month_str = str(month)

            # Aplicar cambio de descuento si existe
            tariff_copy = TariffRecord.from_dict(tariff.__dict__.copy() if hasattr(tariff, '__dict__') else tariff)
            if discount_changes and month_str in discount_changes:
                if tariff_copy.discount is None:
                    tariff_copy.discount = {}
                tariff_copy.discount['percent'] = discount_changes[month_str]

            monthly_cost = self.calculate_monthly_cost(tariff_copy, month_str)
            monthly_costs.append(monthly_cost)
            total_cost += monthly_cost['total_eur']
            total_consumption += monthly_cost['consumption_kwh']

        return {
            'supplier': tariff.supplier,
            'plan_name': tariff.plan_name,
            'source_url': tariff.source_url,
            'extracted_at': tariff.extracted_at,
            'period': f"{start_month} a {end_month}",
            'months': len(monthly_costs),
            'total_consumption_kwh': total_consumption,
            'total_cost_eur': round(total_cost, 2),
            'average_cost_monthly': round(total_cost / len(monthly_costs), 2),
            'monthly_breakdown': monthly_costs,
            'discount': tariff.discount,
            'cashback': tariff.cashback_eur,
            'exit_fee': tariff.exit_fee_eur
        }

    def compare_tariffs(
        self,
        tariffs: List[TariffRecord],
        start_month: str,
        end_month: str,
        reference_tariff: Optional[TariffRecord] = None
    ) -> List[Dict]:
        """
        Comparar múltiples tarifas.
        Retorna lista ordenada por costo total.
        """
        results = []

        for tariff in tariffs:
            result = self.calculate_annual_cost(tariff, start_month, end_month)
            results.append(result)

        # Ordenar por costo
        results = sorted(results, key=lambda x: x['total_cost_eur'])

        # Añadir ahorros respecto a la tarifa de referencia
        if reference_tariff:
            reference_result = self.calculate_annual_cost(reference_tariff, start_month, end_month)
            reference_cost = reference_result['total_cost_eur']

            for result in results:
                result['savings_vs_reference_eur'] = reference_cost - result['total_cost_eur']
                result['savings_vs_reference_percent'] = round(
                    (reference_cost - result['total_cost_eur']) / reference_cost * 100, 2
                )

        return results


def create_default_bord_gais_tariff() -> TariffRecord:
    """Crear registro de la tarifa actual de Bord Gáis (Plan Smart All Day)."""
    return TariffRecord(
        supplier='Bord Gáis',
        plan_name='Smart All Day',
        source_url='https://bordgais.ie/',
        extracted_at='2026-10-01',
        contract_months=12,
        unit_rates_c_per_kwh_ex_vat={
            'day': 38.16,
            'night': 38.16,
            'peak': 38.16
        },
        bands={
            'night': ('21:00', '08:00'),
            'peak': ('17:00', '19:00'),
            'day': 'rest'
        },
        standing_charge_c_per_day=61.52,
        pso_levy_eur_per_month=1.46,
        discount={
            'percent': 32.0,  # hasta 18/08/2026
            'applies_to': 'consumption',
            'months': 12
        },
        cashback_eur=0.0,
        exit_fee_eur=0.0,
        conditions=['direct_debit', 'e_billing']
    )


if __name__ == '__main__':
    print("Electric Switcher - Simulation Engine loaded")
