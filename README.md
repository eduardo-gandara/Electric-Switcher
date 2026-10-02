# Electric Switcher

Aplicación web para análisis y simulación de tarifas eléctricas en Irlanda. Carga tu consumo de ESB Networks, selecciona cómo extraer tarifas (Web Scraping o LLM), compara precios reales de proveedores y descubre cuánto ahorrarías con cada uno.

## 🎯 Características

- **Interfaz web intuitiva**: Upload de CSV, selección de método, comparación visual
- **Motor de simulación**: Reproduce facturas reales con error ≤0,33% (validado contra 4 facturas)
- **Procesamiento de consumo**: Limpia CSV de ESB Networks, imputa huecos, detecta cambios de hora
- **Doble método de recopilación**:
  - 🌐 **Web Scraping**: Extrae tarifas de webs de proveedores con BeautifulSoup
  - 🤖 **LLM (Gemini)**: Analiza páginas web con Google Gemini para extraer datos automáticamente
- **Comparación visual**: Tabla de tarifas con costo anual a 12 meses
- **Breakdown mensual**: Gráfico de desglose de costos mes a mes
- **Fallback inteligente**: Usa datos demo si ambos métodos fallan

## 📋 Requisitos

- Python 3.8+
- Flask
- pandas, numpy, requests, beautifulsoup4
- google-generativeai (para método LLM)

```bash
pip install -r requirements.txt
```

**Variables de entorno** (para LLM Gemini):
```bash
export GEMINI_API_KEY="tu_api_key_aqui"
```

## 🚀 Uso rápido

### Iniciar servidor
```bash
python app.py
```

Abre `http://localhost:5000` en el navegador.

### Flujo de uso
1. **Carga CSV** → Sube archivo de consumo (ESB Networks, últimos 24 meses)
2. **Elige método** → Web Scraping o LLM Gemini para extraer tarifas
3. **Revisa tarifas** → Tabla con planes de 6 proveedores
4. **Compara costos** → Ranking anual + breakdown mensual
5. **Decide** → Identifica mejor opción

## 📊 Arquitectura

```
Frontend (HTML/CSS/JS)
        │
        ▼
┌──────────────────────────────────────┐
│   Flask API (app.py)                 │
│ - POST /api/upload-csv               │
│ - POST /api/collect-tariffs          │
│ - GET /api/tariffs                   │
└──────────┬───────────────────────────┘
           │
    ┌──────┴────────────────────┐
    │                           │
    ▼                           ▼
CSV Processing             Tariff Collection
- ESB Networks            ┌─────────────────┐
- Limpieza                │ Método elegido  │
- Imputation              ├─────────────────┤
- Consumo 30 min          │🌐 Web Scraping  │
                          │ (BeautifulSoup) │
    │                     │                 │
    │                     │🤖 LLM Gemini   │
    │                     │ (Google GenAI)  │
    └─────────┬───────────┴─────────────────┘
              │
              ▼
    ┌──────────────────────────┐
    │ Simulation Engine        │
    │ (src/simulation_engine)  │
    │ - Aplica tarifas        │
    │ - Calcula costos        │
    │ - IVA, descuentos, PSO  │
    │ - Error ≤0,33%          │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ Ranking y Visualización  │
    │ - Tabla de tarifas       │
    │ - Costo anual            │
    │ - Breakdown mensual      │
    │ - Comparativa            │
    └──────────────────────────┘
```

## 🔧 Componentes

### **Backend**

#### `app.py`
Servidor Flask con endpoints REST:
- `POST /api/upload-csv` — Procesa archivo ESB Networks
- `POST /api/collect-tariffs` — Inicia recopilación (Web Scraping o LLM)
- `GET /api/tariffs` — Devuelve tarifas y simulación

#### `src/simulation_engine.py`
Motor determinista (Python + pandas) que aplica tarifas a perfiles de consumo.

**Validación**: 
- Junio 2026: 99,03€ (error 0,0%)
- Julio 2026: 105,72€ (error -0,01%)
- Agosto 2026: 111,67€ (error +0,01%)
- Septiembre 2026: 85,19€ (error -0,33%)

#### `src/consumption_processor.py`
Procesa CSV de ESB Networks: limpia duplicados, imputa huecos, ajusta cambios de hora DST.

#### `agents/tariff_collector.py`
Orquesta la recopilación de tarifas:
- Enruta a Web Scraping o LLM según elección del usuario
- Extrae planes como registros JSON con URL y fecha
- Fallback a demo data si ambos métodos fallan

#### `agents/llm_scraper.py`
Extrae tarifas usando Google Generative AI (Gemini):
- Analiza URLs de proveedores
- Extrae datos estructurados (tasas, cargos, descuentos)
- Solo electricidad, no paquetes combinados

#### `agents/scrapers.py`
Web Scraping con BeautifulSoup:
- Consulta webs de proveedores
- Parsea tablas de tarifas
- Enriquece con metadata

### **Frontend**

#### `templates/index.html`
Interfaz web responsiva:
- Upload de CSV
- Selección de método (Step 1.5)
- Tabla de comparación
- Breakdown mensual con gráficos
- Detalles de tarifa expandibles

## 📈 Datos de entrada

### CSV (ESB Networks)
Formato esperado:
```
MPRN, Meter Serial Number | Read Value | Read Type | Read Date and End Time
[meter_id]                 | [kWh]      | [tipo]    | dd-mm-yyyy hh:mm
```

**Período**: Mínimo 24 meses de datos
**Procesamiento**: 
- Duplicados eliminados
- Huecos imputados (~0,2%)
- Cambios de hora (DST) ajustados automáticamente
- Perfil de consumo por banda (día/noche/pico)

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

## ⚙️ Configuración

### Proveedores soportados (6)
```json
{
  "providers": [
    {"name": "Bord Gáis Energy", "url": "https://www.bordgais.ie/"},
    {"name": "Electric Ireland", "url": "https://www.electricireland.ie/"},
    {"name": "SSE Airtricity", "url": "https://www.sseairtricity.com/"},
    {"name": "Energia", "url": "https://www.energia.ie/"},
    {"name": "Pinergy", "url": "https://www.pinergy.ie/"},
    {"name": "Evoke Energy", "url": "https://www.evokeenergy.ie/"}
  ]
}
```

### Métodos de extracción

**🌐 Web Scraping**
- Usa BeautifulSoup para parsear HTML
- Rápido pero frágil (cambios de estructura HTML rompen)
- Mejor para: Tarifas simples en tablas

**🤖 LLM Gemini**
- Google Generative AI analiza páginas web
- Robusto: entiende contexto, no depende de estructura HTML
- Mejor para: Tarifas complejas, cambios frecuentes en webs
- Requiere: `GEMINI_API_KEY`

### Formato de tarifa extraída
```json
{
  "supplier": "Bord Gáis Energy",
  "plan_name": "Smart Tariff",
  "source_url": "https://www.bordgais.ie/...",
  "extracted_at": "2026-10-02T10:30:00",
  "unit_rates_c_per_kwh_ex_vat": {
    "day": 24.6,
    "night": 13.8,
    "peak": null
  },
  "standing_charge_c_per_day": 41.2,
  "pso_levy_eur_per_month": 11.5,
  "discount": {"percent": 15, "applies_to": "consumption"},
  "cashback_eur": 50.0,
  "exit_fee_eur": 0.0,
  "contract_months": 12
}
```

## ✅ Criterios de éxito

1. ✓ Motor reproduce 4 facturas reales con error ≤0,33%
2. ✓ Extrae tarifas de 6 proveedores automáticamente (Web o LLM)
3. ✓ Interfaz web intuitiva: upload → selección método → comparación
4. ✓ Fallback a demo data si extracción falla
5. ✓ Breakdown mensual con tabla clara (24 meses)

## 🚨 Riesgos y limitaciones

- **Descuentos de nuevo cliente**: Bajan del 32% al 28% tras primer año
- **Datos desactualizados**: Tarifas pueden cambiar, especialmente en mercado volátil
- **LLM puede fallar**: Gemini extrae datos, pero puede perder campos en tarifas complejas
- **Cambios en el hogar**: EV, bomba de calor → consumo diferente, requiere nuevo CSV
- **Franjas inconsistentes**: Cada proveedor define bandas distintas (día/noche/pico)
- **Web Scraping frágil**: Cambios en estructura HTML rompen parseo
- **Validación limitada**: Fallback a demo data si ambos métodos fallan (datos ficticios)

## 📋 Plan de construcción (fases)

- ✅ **Fase 0**: Base validada. CSV + 4 facturas procesadas
- ✅ **Fase 1**: Motor reutilizable. Esquema JSON + tarifa actual
- ✅ **Fase 2**: Recopilador web + LLM. Selección de método (Web Scraping vs Gemini), extracción automática de 6 proveedores, fallback a demo data
- ⏳ **Fase 3**: Ranking y asesor. Análisis de riesgo, sensibilidad a consumo (+/-20%), recomendaciones personalizadas
- ⏳ **Fase 4**: Persistencia. Base de datos de tarifas, histórico de cambios, caché inteligente
- ⏳ **Fase 5**: Versión 2.0. Escenarios (EV, bomba de calor), notificaciones, API pública

## 🤔 Próximas mejoras (Fase 3+)

- [ ] Análisis de sensibilidad (impacto de +/-20% consumo)
- [ ] Recomendaciones personalizadas por riesgo
- [ ] Base de datos de tarifas (persistencia)
- [ ] Histórico de cambios de tarifas
- [ ] Notificaciones de cambios significativos
- [ ] API REST pública
- [ ] Escenarios de consumo futuro (EV, energías renovables)
- [ ] Exportar a PDF/Excel
- [ ] Autenticación de usuarios
- [ ] Dashboard personal

## 🔄 Desarrollo

### Estructura de directorios
```
Electric-Switcher/
├── app.py                      # Servidor Flask
├── templates/
│   └── index.html             # Interfaz web
├── src/
│   ├── simulation_engine.py   # Motor de cálculo
│   ├── consumption_processor.py
│   └── main.py                # CLI (legacy)
├── agents/
│   ├── tariff_collector.py    # Orquestador
│   ├── llm_scraper.py         # Gemini API
│   └── scrapers.py            # BeautifulSoup
├── config/
│   └── providers.json         # Configuración de proveedores
├── uploads/                   # CSV subidos
└── data/
    └── demo_tariffs.json      # Datos fallback
```

### Cómo extender

**Agregar nuevo proveedor**: Edita `config/providers.json` + implanta scraper en `agents/scrapers.py`

**Mejorar LLM**: Modifica prompt en `agents/llm_scraper.py:_extract_tariffs_with_llm()`

**Cambiar interfaz**: Edita `templates/index.html` (HTML/CSS/JS) + endpoints en `app.py`

### Testing
```bash
# Simulación con datos demo
python src/main.py --demo

# Con CSV real
python src/main.py --csv data/consumo_esb.csv --method=llm
```

## 📝 Licencia

Ejercicio de demostración para entender AI agents de punta a punta.

## 👤 Autor

Eduardo Gándara (2026)
Co-authored with Claude Haiku 4.5
