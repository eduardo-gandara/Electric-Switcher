# Tariff Collector Agent

El Agente Recopilador (`TariffCollector`) busca y extrae tarifas de electricidad de proveedores irlandeses.

## Características

✅ **Validación de Fuentes** - Solo acepta datos de páginas oficiales de proveedores
✅ **Normalización** - Convierte precios a c/kWh sin IVA
✅ **Trazabilidad** - Cada tarifa lleva URL y fecha de extracción
✅ **Rechazo Automático** - Rechaza tariffs con datos faltantes o implausibles
✅ **Exportación JSON** - Genera archivo de tarifas listo para la simulación

## Proveedores Soportados

- Bord Gáis Energy
- Electric Ireland
- SSE Airtricity
- Energia
- Pinergy
- Evoke Energy

## Uso

### 1. Desde la línea de comandos

```bash
# Ver reporte de recopilación
python3 collect_tariffs.py --report

# Recopilar y mostrar tarifas
python3 collect_tariffs.py

# Recopilar y exportar a JSON
python3 collect_tariffs.py --export
python3 collect_tariffs.py --export --output custom_tariffs.json
```

### 2. Desde la API

```bash
# POST /api/collect-tariffs
curl -X POST http://localhost:5000/api/collect-tariffs \
  -H "Content-Type: application/json"
```

Respuesta:
```json
{
  "success": true,
  "report": {
    "timestamp": "2026-10-02T01:37:41.418945",
    "providers_scraped": 6,
    "tariffs_collected": 3,
    "tariffs_rejected": 0,
    "suppliers": ["Bord Gáis Energy", "Electric Ireland", "SSE Airtricity"]
  },
  "tariffs": [
    {
      "supplier": "Bord Gáis Energy",
      "plan_name": "Smart All Day",
      "source_url": "https://...",
      "extracted_at": "2026-09-28",
      "unit_rates_c_per_kwh_ex_vat": {"day": 27.5, "night": 15.2, "peak": 35.8},
      "standing_charge_c_per_day": 43.5,
      "pso_levy_eur_per_month": 11.5,
      "discount": {"percent": 32, "applies_to": "consumption", "months": 12},
      ...
    }
  ],
  "rejected": [],
  "exported_to": "/path/to/tariffs_example.json"
}
```

### 3. Desde Python

```python
from agents.tariff_collector import TariffCollector

collector = TariffCollector()
collected, rejected = collector.collect_all()

# Mostrar tarifas recopiladas
for tariff in collected:
    print(f"{tariff.supplier} - {tariff.plan_name}")
    print(f"  Source: {tariff.source_url}")
    print(f"  Rates: {tariff.unit_rates_c_per_kwh_ex_vat}")

# Exportar a JSON
output_file = collector.export_to_json('my_tariffs.json')
print(f"Exported to {output_file}")

# Ver reporte
report = collector.get_report()
print(f"Collected: {report['tariffs_collected']}")
print(f"Rejected: {report['tariffs_rejected']}")
```

## Reglas de Validación (según TDD)

1. **Fuentes Oficiales**: Solo se acepta datos de páginas abiertas de proveedores oficiales, no de fragmentos de buscador.

2. **Precios Válidos**: El coste solo es válido si procede de:
   - Página oficial del proveedor eléctrico
   - Comparadores reconocidos
   - Agregadores de datos
   - Prensa especializada

3. **Sin Promedios**: Dos fuentes que discrepan en precio dejan el plan marcado para revisión humana, nunca se promedian.

4. **Campos Nulos**: Un campo que el proveedor no publica se guarda como `null`, nunca se estima.

5. **Normalización**: Cada precio se normaliza a c/kWh sin IVA y se anota si la fuente lo publicaba con IVA.

## Estructura de Tarifa

```python
{
    "supplier": "Bord Gáis Energy",          # Nombre del proveedor
    "plan_name": "Smart All Day",            # Nombre del plan
    "source_url": "https://...",             # URL de origen
    "extracted_at": "2026-09-28",            # Fecha de extracción
    "contract_months": 12,                   # Duración del contrato
    "unit_rates_c_per_kwh_ex_vat": {         # Precios por banda (c/kWh sin IVA)
        "day": 27.5,
        "night": 15.2,
        "peak": 35.8
    },
    "bands": {                               # Horarios de las bandas
        "night": ["21:00", "08:00"],
        "peak": ["17:00", "19:00"]
    },
    "standing_charge_c_per_day": 43.5,       # Cargo fijo (c/día)
    "pso_levy_eur_per_month": 11.5,          # Gravamen PSO (€/mes)
    "discount": {                            # Descuento
        "percent": 32,
        "applies_to": "consumption",
        "months": 12
    },
    "cashback_eur": 0.0,                     # Cashback (€)
    "exit_fee_eur": 0.0,                     # Penalización de salida (€)
    "conditions": ["Direct debit", "E-billing"]  # Condiciones
}
```

## Campos Rechazados

Tariffs que no cumplen las validaciones:

```python
{
    "supplier": "Provider Name",
    "plan_name": "Plan Name",
    "reason": "Missing unit rates" | "Price out of range" | etc,
    "source_url": "https://..." (opcional)
}
```

## Estado Actual

✅ **Fase 1 - Recopilación**: Funcional con datos demo
⏳ **Fase 2 - Web Scraping**: En desarrollo (integración con BeautifulSoup)
⏳ **Fase 3 - Validación Automática**: Verificación contra múltiples fuentes

## Próximos Pasos

1. Implementar web scraping real con BeautifulSoup para cada proveedor
2. Añadir validación contra múltiples fuentes
3. Implementar alertas para precios fuera de rango
4. Crear scheduler para actualizar tarifas diariamente

