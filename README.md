# Electric Switcher

Sistema de análisis y simulación de tarifas eléctricas en Irlanda. Calcula cuánto pagarías con cada tarifa aplicándola a tu consumo real de 30 minutos, y te ayuda a decidir si cambiar de proveedor.

## 🎯 Características

- **Motor de simulación**: Reproduce facturas reales con error ≤2% (validado contra 4 facturas)
- **Procesamiento de consumo**: Limpia CSV de ESB Networks, imputa huecos, detecta cambios de hora
- **Recopilación de tarifas**: Extrae planes de proveedores irlandeses (Bord Gáis, Electric Ireland, Energia, etc.)
- **Ranking inteligente**: Compara tarifas a 12 meses con sensibilidad a consumo (+20%, -20%)
- **Asesor**: Identifica riesgos, supuestos y recomendaciones

## 📋 Requisitos

- Python 3.8+
- pandas, numpy, requests, beautifulsoup4

```bash
pip install -r requirements.txt
```

## 🚀 Uso rápido

### Modo demo
```bash
python src/main.py --demo
```

### Con datos reales
```bash
python src/main.py --csv datos/consumo_esb.csv --tariffs config/tarifas.json
```

### Pruebas de validación
```bash
python test_simulation.py
```

## 📊 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    CSV ESB Networks                         │
│              (kWh cada 30 min, 24 meses)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Agente: Analista de Consumo                      │
│  - Limpia: duplicados, huecos (~0,2%), cambios de hora     │
│  - Construye: perfil por banda (día/noche/pico) + hora     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│      Motor de Simulación (código determinista)      │
│  - Aplica cada tarifa al perfil de 30 minutos       │
│  - Calcula costo con IVA, descuentos, cargos        │
│  - Validado: error ≤0,33% en 4 facturas reales      │
└──────────────────────────┬───────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐   ┌──────────┐      ┌──────────┐
    │  Bord    │   │ Electric │      │ Energia  │
    │  Gáis    │   │ Ireland  │      │    ...   │
    │ €84-110  │   │ €78-105  │      │ €82-108  │
    └──────────┘   └──────────┘      └──────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │    Agente: Asesor                    │
        │ - Ranking por costo neto a 12 meses │
        │ - Análisis de riesgo y supuestos     │
        │ - Recomendaciones para usuario       │
        └──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   El usuario decide                  │
        │ - Cambiar de proveedor               │
        │ - Mantener el actual                 │
        └──────────────────────────────────────┘
```

## 🔧 Componentes

### `src/simulation_engine.py`
Motor determinista (Python + pandas) que aplica tarifas a perfiles de consumo.

**Validación**: 
- Junio 2026: 99,03€ (error 0,0%)
- Julio 2026: 105,72€ (error -0,01%)
- Agosto 2026: 111,67€ (error +0,01%)
- Septiembre 2026: 85,19€ (error -0,33%)

### `src/consumption_processor.py`
Procesa CSV de ESB Networks: limpia duplicados, imputa huecos, ajusta cambios de hora DST.

### `agents/tariff_collector.py`
Busca en webs de proveedores irlandeses, extrae planes como registros JSON con URL y fecha.

### `agents/advisor.py`
Presenta ranking, calcula ahorros, analiza sensibilidad, identifica riesgos.

### `src/main.py`
Orquesta el pipeline completo: consumo → validación → simulación → informe.

## 📈 Datos de entrada

### CSV (ESB Networks)
```
MPRN, Meter Serial Number | Read Value | Read Type | Read Date and End Time
[meter_id]                 | [kWh]      | [tipo]    | dd-mm-yyyy hh:mm
```

**Período**: 01/10/2024 a 30/09/2026 (24 meses)
**Limpieza**: Duplicados eliminados, ~80 intervalos imputados, DST ajustado

### Registro de tarifa (JSON)
```json
{
  "supplier": "string",
  "plan_name": "string",
  "source_url": "https://...",
  "extracted_at": "2026-10-01",
  "contract_months": 12,
  "unit_rates_c_per_kwh_ex_vat": {
    "day": 38.16,
    "night": 38.16,
    "peak": 38.16
  },
  "bands": {
    "night": ["21:00", "08:00"],
    "peak": ["17:00", "19:00"],
    "day": "rest"
  },
  "standing_charge_c_per_day": 61.52,
  "pso_levy_eur_per_month": 1.46,
  "discount": {
    "percent": 32.0,
    "applies_to": "consumption",
    "months": 12
  },
  "cashback_eur": 0.0,
  "exit_fee_eur": 0.0,
  "conditions": ["direct_debit", "e_billing"]
}
```

## 💰 Fórmula de coste

```
Coste = (1 + IVA%) × [Σ_b (kWh_b × p_b × (1-d%)) + SC + PSO] - cashback
```

donde:
- b ∈ {day, night, peak}
- SC = standing charge diario × días del mes
- PSO = PSO levy mensual
- IVA = 9%

**Franjas**:
- Night (noche): 21:00-08:00 → todos los días
- Peak (pico): 17:00-19:00 → solo lunes-viernes
- Day (día): resto

## ✅ Criterios de éxito

1. ✓ Motor reproduce 4 facturas reales con error ≤2% (actualmente ≤0,33%)
2. ✓ Cada tarifa en ranking lleva URL y fecha de extracción
3. ✓ Humano revisa mejores 3 opciones antes de decidir

## 🚨 Riesgos identificados

- **Descuentos de nuevo cliente**: Bajan del 32% al 28% tras primer año
- **Datos desactualizados**: Verificar en web oficial si >7 días
- **Cambios en el hogar**: EV, bomba de calor → recalcular
- **Franjas inconsistentes**: Cada proveedor define bandas distintas

## 📋 Plan de construcción (fases)

- ✅ **Fase 0**: Base validada. CSV + 4 facturas procesadas
- ✅ **Fase 1**: Motor reutilizable. Esquema JSON + tarifa actual
- ⏳ **Fase 2**: Agente recopilador. Búsqueda web de proveedores
- ⏳ **Fase 3**: Ranking y asesor. Simulación + análisis de riesgo
- ⏳ **Fase 4**: Versión 2. Escenarios de consumo (EV, bomba de calor)
- ⏳ **Fase 5**: Presentación. Slide + demostración interactiva

## 🤔 Próximas mejoras

- [ ] Extracción automatizada de tarifas desde webs
- [ ] Escenarios de consumo futuro (EV, energías renovables)
- [ ] Comparación con otros usuarios
- [ ] Notificaciones de cambios de tarifa
- [ ] Integración con APIs de proveedores

## 📝 Licencia

Ejercicio de demostración para entender AI agents de punta a punta.

## 👤 Autor

Eduardo Gándara (2026)
