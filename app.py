"""
Electric Switcher - API Flask
Backend server that runs the simulation engine
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Agregar rutas
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.simulation_engine import SimulationEngine, ConsumptionProfile, TariffRecord, create_default_bord_gais_tariff
from src.consumption_processor import ConsumptionProcessor
from agents.advisor import AdvisorAgent
from agents.tariff_collector import TariffCollector

# Custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Period):
            return str(obj)
        return super().default(obj)


def convert_numpy_types(obj):
    """Recursively convert numpy types to Python natives."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Period):
        return str(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj

app = Flask(__name__)
CORS(app)
app.json_encoder = NumpyEncoder
app.json.encoder_class = NumpyEncoder

# Directorio para archivos subidos
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')


@app.route('/api/tariffs', methods=['GET'])
def get_tariffs():
    """Obtener tarifas disponibles."""
    tariffs_file = Path(__file__).parent / 'config' / 'tariffs_example.json'

    if tariffs_file.exists():
        with open(tariffs_file, 'r', encoding='utf-8') as f:
            tariffs = json.load(f)
        return jsonify({'success': True, 'tariffs': tariffs})

    # Tarifa por defecto si no hay archivo
    default = create_default_bord_gais_tariff()
    return jsonify({
        'success': True,
        'tariffs': [default.__dict__]
    })


@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    """Subir y procesar CSV de consumo."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Must be CSV file'}), 400

        # Sanitize filename to avoid issues
        import time
        safe_filename = f"upload_{int(time.time())}_{file.filename}"
        filepath = UPLOAD_FOLDER / safe_filename

        # Read file content into memory first to avoid file locking issues
        file_content = file.read()
        if not file_content:
            return jsonify({'success': False, 'error': 'File is empty'}), 400

        # Write to disk
        with open(filepath, 'wb') as f:
            f.write(file_content)

        # Procesar CSV
        processor = ConsumptionProcessor(str(filepath))
        processor.clean()

        # Validar
        valid, msg = processor.validate()
        quality = convert_numpy_types(processor.get_quality_report())

        return jsonify({
            'success': True,
            'filename': safe_filename,
            'valid': valid,
            'message': msg,
            'quality': quality
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Upload error: {str(e)}\n{error_details}", flush=True)
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'}), 500


@app.route('/api/process-csv', methods=['POST'])
def process_csv():
    """Procesar CSV que ya existe en uploads folder."""
    try:
        filename = request.form.get('filename', '')

        if not filename:
            return jsonify({'success': False, 'error': 'No filename provided'}), 400

        filepath = UPLOAD_FOLDER / filename
        if not filepath.exists():
            return jsonify({'success': False, 'error': f'File not found: {filename}'}), 400

        # Procesar CSV
        processor = ConsumptionProcessor(str(filepath))
        processor.clean()

        # Validar
        valid, msg = processor.validate()
        quality = convert_numpy_types(processor.get_quality_report())

        return jsonify({
            'success': True,
            'filename': filename,
            'valid': valid,
            'message': msg,
            'quality': quality
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Ejecutar simulación."""
    try:
        data = request.json

        # Validar entrada
        if 'csv_filename' not in data or 'tariffs' not in data:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400

        csv_filename = data['csv_filename']
        tariffs_data = data['tariffs']

        # Cargar CSV
        csv_path = UPLOAD_FOLDER / csv_filename
        if not csv_path.exists():
            return jsonify({'success': False, 'error': f'CSV file not found: {csv_filename}'}), 400

        # Procesar consumo
        try:
            processor = ConsumptionProcessor(str(csv_path))
            processor.clean()
            profile_df = processor.build_profile()
            consumption_profile = ConsumptionProfile(profile_df)
        except Exception as e:
            return jsonify({'success': False, 'error': f'CSV processing error: {str(e)}'}), 400

        # Auto-detectar rango de fechas completo del CSV
        start_month = None
        end_month = None
        if profile_df is not None and len(profile_df) > 0:
            min_date = profile_df['timestamp'].min()
            max_date = profile_df['timestamp'].max()
            if pd.notna(min_date) and pd.notna(max_date):
                start_month = min_date.strftime('%Y-%m')
                end_month = max_date.strftime('%Y-%m')

        if not start_month or not end_month:
            return jsonify({'success': False, 'error': 'Invalid date range in CSV'}), 400

        # Crear tarifas
        tariffs = [TariffRecord.from_dict(t) for t in tariffs_data]

        # Ejecutar simulación
        engine = SimulationEngine(consumption_profile)
        reference_tariff = create_default_bord_gais_tariff()

        results = engine.compare_tariffs(
            tariffs,
            start_month,
            end_month,
            reference_tariff
        )

        # Generar informe del asesor
        advisor = AdvisorAgent()
        report = advisor.create_report(
            results,
            reference_tariff=results[0],
            scenarios={'base': 1.0, '+20%': 1.2, '-20%': 0.8}
        )

        # Convertir a tipos JSON-serializable
        results = convert_numpy_types(results)
        report = convert_numpy_types(report)

        return jsonify({
            'success': True,
            'results': results,
            'report': report
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Simulation error: {str(e)}'}), 500


@app.route('/api/demo-simulate', methods=['POST'])
def demo_simulate():
    """Ejecutar simulación con datos de demo."""
    try:
        data = request.json
        tariffs_data = data.get('tariffs', [])

        # Crear perfil de ejemplo
        monthly_data = {
            '2026-06': 271,
            '2026-07': 297,
            '2026-08': 311,
            '2026-09': 217,
        }

        profiles = {}
        for month_str, total_kwh in monthly_data.items():
            month = pd.Period(month_str, 'M')
            intervals = month.days_in_month * 48
            kwh_per_interval = total_kwh / intervals

            month_start = month.to_timestamp()
            timestamps = pd.date_range(month_start, periods=intervals, freq='30min')

            df = pd.DataFrame({
                'timestamp': timestamps,
                'kwh': [kwh_per_interval] * intervals,
                'band': 'day'
            })

            profiles[month_str] = ConsumptionProfile(df)

        # Combinar perfiles
        dfs = []
        for month_str in sorted(monthly_data.keys()):
            dfs.append(profiles[month_str].df.copy())

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_profile = ConsumptionProfile(combined_df)

        # Crear tarifas
        if not tariffs_data:
            tariffs = [create_default_bord_gais_tariff()]
        else:
            tariffs = [TariffRecord.from_dict(t) for t in tariffs_data]

        # Ejecutar simulación
        engine = SimulationEngine(combined_profile)
        results = engine.compare_tariffs(
            tariffs,
            '2026-06',
            '2026-09',
            reference_tariff=create_default_bord_gais_tariff()
        )

        # Generar informe
        advisor = AdvisorAgent()
        report = advisor.create_report(results)

        # Convertir a tipos JSON-serializable
        results = convert_numpy_types(results)
        report = convert_numpy_types(report)

        return jsonify({
            'success': True,
            'results': results,
            'report': report
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/collect-tariffs', methods=['POST'])
def collect_tariffs():
    """Run tariff collector agent."""
    try:
        collector = TariffCollector()
        collected, rejected = collector.collect_all()

        # Convert to JSON-serializable format
        collected_dicts = [convert_numpy_types(t.to_dict()) for t in collected]
        rejected_dicts = [convert_numpy_types({
            'supplier': r.supplier,
            'plan_name': r.plan_name,
            'reason': r.reason,
            'source_url': r.source_url
        }) for r in rejected]

        # Export to file
        output_file = collector.export_to_json('tariffs_example.json')

        return jsonify({
            'success': True,
            'report': collector.get_report(),
            'tariffs': collected_dicts,
            'rejected': rejected_dicts,
            'exported_to': output_file
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
