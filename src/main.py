"""
Electric Switcher - Main Application
Flujo completo: consumo -> simulación -> ranking -> decisión
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Agregar rutas
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation_engine import SimulationEngine, ConsumptionProfile, create_default_bord_gais_tariff, TariffRecord
from consumption_processor import ConsumptionProcessor
from agents.advisor import AdvisorAgent
from agents.tariff_collector import TariffCollectorAgent


class ElectricSwitcherApp:
    """Aplicación principal de Electric Switcher."""

    def __init__(self, csv_path: str = None, tariffs_path: str = None):
        self.csv_path = csv_path
        self.tariffs_path = tariffs_path
        self.consumption_profile = None
        self.tariffs = []
        self.simulation_engine = None
        self.comparison_results = None

    def process_consumption(self, csv_path: str) -> bool:
        """Procesar datos de consumo de ESB Networks."""
        print(f"\n📂 Procesando consumo desde: {csv_path}")

        try:
            processor = ConsumptionProcessor(csv_path)
            processor.clean()

            # Validar
            valid, msg = processor.validate()
            print(f"  {msg}")

            quality = processor.get_quality_report()
            print(f"  Rango: {quality.get('date_range')}")
            print(f"  Filas procesadas: {quality.get('final_rows')}")

            # Construir perfil
            profile_df = processor.build_profile()
            self.consumption_profile = ConsumptionProfile(profile_df)

            print(f"  ✓ Perfil de consumo construido")
            return True

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def load_tariffs(self, tariffs_path: str = None) -> bool:
        """Cargar tarifas desde JSON."""
        if not tariffs_path and self.tariffs_path:
            tariffs_path = self.tariffs_path

        if tariffs_path and Path(tariffs_path).exists():
            print(f"\n💰 Cargando tarifas desde: {tariffs_path}")
            try:
                with open(tariffs_path, 'r', encoding='utf-8') as f:
                    tariffs_data = json.load(f)
                    self.tariffs = [TariffRecord.from_dict(t) for t in tariffs_data]
                    print(f"  ✓ {len(self.tariffs)} tarifas cargadas")
                    return True
            except Exception as e:
                print(f"  ✗ Error cargando tarifas: {e}")

        return False

    def collect_tariffs(self) -> bool:
        """Recopilar tarifas de proveedores."""
        print(f"\n🔍 Recopilando tarifas de proveedores irlandeses...")

        try:
            collector = TariffCollectorAgent()
            self.tariffs = collector.collect_all()

            if self.tariffs:
                print(f"  ✓ {len(self.tariffs)} tarifas recopiladas")
                return True
            else:
                print(f"  ⚠️  No se encontraron tarifas")
                return False

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def run_simulation(
        self,
        start_month: str = '2026-06',
        end_month: str = '2026-09',
        reference_tariff: TariffRecord = None
    ) -> bool:
        """Ejecutar simulación de tarifas."""
        if not self.consumption_profile:
            print("✗ Error: Cargue primero datos de consumo")
            return False

        if not self.tariffs:
            print("⚠️  Sin tarifas para simular. Usando tarifa de referencia...")
            self.tariffs = [create_default_bord_gais_tariff()]

        print(f"\n⚙️  Ejecutando simulación ({start_month} a {end_month})...")

        try:
            self.simulation_engine = SimulationEngine(self.consumption_profile)

            # Tarifa de referencia (actual)
            if not reference_tariff:
                reference_tariff = create_default_bord_gais_tariff()

            # Comparar tarifas
            self.comparison_results = self.simulation_engine.compare_tariffs(
                self.tariffs,
                start_month,
                end_month,
                reference_tariff
            )

            print(f"  ✓ {len(self.comparison_results)} tarifas simuladas")
            return True

        except Exception as e:
            print(f"  ✗ Error en simulación: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_report(self, reference_tariff: TariffRecord = None) -> str:
        """Generar informe de asesor."""
        if not self.comparison_results:
            print("✗ Error: Ejecute simulación primero")
            return ""

        print(f"\n📊 Generando informe...")

        try:
            advisor = AdvisorAgent()

            if not reference_tariff:
                reference_tariff = create_default_bord_gais_tariff()

            # Obtener costo de referencia
            ref_result = None
            if self.simulation_engine:
                ref_result = self.simulation_engine.calculate_annual_cost(
                    reference_tariff,
                    '2026-06',
                    '2026-09'
                )

            report = advisor.create_report(
                self.comparison_results,
                reference_tariff=ref_result,
                scenarios={'base': 1.0, '+20%': 1.2, '-20%': 0.8}
            )

            formatted = advisor.format_for_user(report)
            print(formatted)

            return json.dumps(report, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"  ✗ Error generando informe: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def save_results(self, output_dir: str = 'results'):
        """Guardar resultados en archivos."""
        Path(output_dir).mkdir(exist_ok=True)

        # Guardar resultados de comparación
        if self.comparison_results:
            results_file = Path(output_dir) / 'comparison_results.json'
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.comparison_results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n💾 Resultados guardados en {results_file}")

    def run_full_pipeline(self, csv_path: str, tariffs_path: str = None):
        """Ejecutar pipeline completo."""
        print("\n" + "="*60)
        print("ELECTRIC SWITCHER - PIPELINE COMPLETO")
        print("="*60)

        # 1. Procesar consumo
        if not self.process_consumption(csv_path):
            print("✗ No se pudo procesar consumo. Abortando.")
            return False

        # 2. Cargar o recopilar tarifas
        if tariffs_path:
            self.load_tariffs(tariffs_path)
        else:
            print("\n⚠️  Sin archivo de tarifas. Crear tarifas.json o ejecutar recopilador...")

        # 3. Si no hay tarifas, usar solo referencia
        if not self.tariffs:
            print("⚠️  Usando solo tarifa de referencia para demostración")
            self.tariffs = [create_default_bord_gais_tariff()]

        # 4. Ejecutar simulación
        if not self.run_simulation('2026-06', '2026-09'):
            return False

        # 5. Generar informe
        report = self.generate_report()

        # 6. Guardar resultados
        self.save_results()

        return True


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Electric Switcher - Análisis de tarifas eléctricas irlandesas'
    )
    parser.add_argument(
        '--csv', type=str, help='Ruta del CSV de consumo (ESB Networks)'
    )
    parser.add_argument(
        '--tariffs', type=str, help='Ruta del archivo JSON de tarifas'
    )
    parser.add_argument(
        '--demo', action='store_true', help='Ejecutar en modo demo (datos de ejemplo)'
    )

    args = parser.parse_args()

    # Crear aplicación
    app = ElectricSwitcherApp(csv_path=args.csv, tariffs_path=args.tariffs)

    if args.demo:
        # Modo demo
        print("\n" + "="*60)
        print("ELECTRIC SWITCHER - MODO DEMO")
        print("="*60)

        print("\n✓ Demostración de motor de simulación")
        print("  (Ejecutar con --csv <path> para procesar datos reales)")

        # Crear perfil de ejemplo
        example_data = pd.DataFrame({
            'timestamp': pd.date_range('2026-06-01', periods=1440, freq='30min'),
            'kwh': [12.5] * 1440,  # ~4.380 kWh mensuales
            'band': ['day'] * 1440
        })

        profile = ConsumptionProfile(example_data)
        engine = SimulationEngine(profile)

        # Simular tarifa de referencia
        reference = create_default_bord_gais_tariff()
        result = engine.calculate_annual_cost(reference, '2026-06', '2026-09')

        print(f"\n  Costo estimado (Bord Gáis): {result['total_cost_eur']:.2f}€")
        print(f"  Consumo: {result['total_consumption_kwh']:.0f} kWh")

    elif args.csv:
        # Pipeline con datos reales
        success = app.run_full_pipeline(args.csv, args.tariffs)
        if not success:
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
