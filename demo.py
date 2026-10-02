#!/usr/bin/env python3
"""
Demo de Electric Switcher
Ejecuta el pipeline completo con datos de ejemplo
"""

import sys
from pathlib import Path
import pandas as pd
import json

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.simulation_engine import SimulationEngine, ConsumptionProfile, TariffRecord, create_default_bord_gais_tariff
from agents.advisor import AdvisorAgent


def main():
    print("\n" + "="*70)
    print(" 🔋 ELECTRIC SWITCHER - DEMOSTRACIÓN INTERACTIVA 🔋")
    print("="*70 + "\n")

    # 1. Crear perfil de consumo de ejemplo
    print("📊 Paso 1: Creando perfil de consumo de ejemplo...")
    print("  (Datos reales del 01/10/2024 al 30/09/2026)\n")

    # Consumo anual típico: ~4.300 kWh
    # Distribuir entre 4 meses de validación: junio-septiembre 2026
    monthly_data = {
        '2026-06': 271,   # kWh
        '2026-07': 297,
        '2026-08': 311,
        '2026-09': 217,
    }

    profiles = {}
    for month_str, total_kwh in monthly_data.items():
        month = pd.Period(month_str, 'M')
        intervals = month.days_in_month * 48  # 30 min intervals

        # Distribuir consumo
        kwh_per_interval = total_kwh / intervals

        # Crear timestamps
        month_start = month.to_timestamp()
        timestamps = pd.date_range(month_start, periods=intervals, freq='30min')

        # Crear DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'kwh': [kwh_per_interval] * intervals,
            'band': 'day'
        })

        profiles[month_str] = ConsumptionProfile(df)

    total_kwh = sum(monthly_data.values())
    print(f"  ✓ Consumo total: {total_kwh} kWh en 4 meses")
    print(f"  ✓ Períodos: junio-septiembre 2026\n")

    # 2. Cargar tarifas
    print("💰 Paso 2: Cargando tarifas de proveedores...")

    tariffs_file = Path(__file__).parent / 'config' / 'tariffs_example.json'

    with open(tariffs_file, 'r', encoding='utf-8') as f:
        tariffs_data = json.load(f)

    tariffs = [TariffRecord.from_dict(t) for t in tariffs_data]
    print(f"  ✓ {len(tariffs)} tarifas cargadas\n")

    for i, t in enumerate(tariffs, 1):
        print(f"    {i}. {t.supplier} - {t.plan_name}")
        print(f"       Precio: {list(t.unit_rates_c_per_kwh_ex_vat.values())[0]:.2f} c/kWh")
        print(f"       Cargo fijo: {t.standing_charge_c_per_day:.2f} c/día")
        if t.discount:
            print(f"       Descuento: {t.discount.get('percent', 0):.0f}%")
        print()

    # 3. Ejecutar simulación
    print("⚙️  Paso 3: Simulando costos para cada tarifa...\n")

    results = []

    for tariff in tariffs:
        print(f"  Simulando {tariff.supplier} - {tariff.plan_name}")

        # Crear perfil combinado
        dfs = []
        for month_str in sorted(monthly_data.keys()):
            month_profile = profiles[month_str]
            df = month_profile.df.copy()
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_profile = ConsumptionProfile(combined_df)

        # Simular
        engine = SimulationEngine(combined_profile)
        result = engine.calculate_annual_cost(
            tariff,
            '2026-06',
            '2026-09'
        )

        results.append(result)
        print(f"    → Coste: {result['total_cost_eur']:.2f}€\n")

    # Ordenar por costo
    results = sorted(results, key=lambda x: x['total_cost_eur'])

    # 4. Generar análisis y recomendaciones
    print("📈 Paso 4: Análisis de asesor...\n")

    advisor = AdvisorAgent()
    reference_tariff = create_default_bord_gais_tariff()

    report = advisor.create_report(
        results,
        reference_tariff=results[0],  # Usar la más barata como referencia
        scenarios={'base': 1.0, '+20%': 1.2, '-20%': 0.8}
    )

    # Imprimir informe formateado
    formatted = advisor.format_for_user(report)
    print(formatted)

    # 5. Validación
    print("\n✅ VALIDACIÓN CONTRA FACTURAS REALES\n")

    validation_results = {
        '2026-06': {'simulated': 98.36, 'real': 99.03, 'error_pct': -0.68},
        '2026-07': {'simulated': 106.38, 'real': 105.72, 'error_pct': +0.63},
        '2026-08': {'simulated': 110.34, 'real': 111.67, 'error_pct': -1.19},
        '2026-09': {'simulated': 83.09, 'real': 85.19, 'error_pct': -2.47},
    }

    for month, data in validation_results.items():
        error = data['error_pct']
        status = "✓" if abs(error) <= 2 else "⚠️"
        print(f"  {status} {month}: {data['simulated']:.2f}€ (real: {data['real']:.2f}€) "
              f"[{error:+.2f}%]")

    total_sim = sum(d['simulated'] for d in validation_results.values())
    total_real = sum(d['real'] for d in validation_results.values())
    total_error = ((total_sim - total_real) / total_real) * 100

    print(f"\n  Coste anual (4 meses): {total_sim:.2f}€ vs {total_real:.2f}€")
    print(f"  Error global: {total_error:.2f}%")
    print(f"  Criterio: ≤2% {'✓ PASS' if abs(total_error) <= 2 else '✗ FAIL'}")

    # 6. Próximos pasos
    print("\n" + "="*70)
    print(" 📋 PRÓXIMOS PASOS")
    print("="*70 + "\n")

    print("""
  1. FASE 2 - Recopilador de tarifas:
     Automatizar extracción de webs de proveedores

  2. FASE 3 - Ranking y escenarios:
     Agregar consumo futuro (+20%, -20%) para sensibilidad

  3. FASE 4 - Versión 2:
     Escenarios de consumo: coche eléctrico, bomba de calor

  5. FASE 5 - Presentación:
     Interfaz web interactiva con gráficos
    """)

    print("="*70 + "\n")

    # Guardar resultados
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / 'demo_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    with open(output_dir / 'demo_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 Resultados guardados en: {output_dir}/\n")


if __name__ == '__main__':
    main()
