# 🌐 Interfaz Web de Electric Switcher

Interfaz web moderna y interactiva para ejecutar simulaciones de tarifas eléctricas.

## 🚀 Inicio Rápido

### Opción 1: Script automático (recomendado)

```bash
cd /home/gandara/Projects/Electric-Switcher
chmod +x run_web.sh
./run_web.sh
```

Luego abre en tu navegador: **http://localhost:5000**

### Opción 2: Manual con Flask

```bash
cd /home/gandara/Projects/Electric-Switcher
source venv/bin/activate
python3 app.py
```

Luego abre: **http://localhost:5000**

## 🎨 Características de la Interfaz

### Diseño Responsivo
- ✅ Funciona en desktop, tablet y móvil
- ✅ Gradiente moderno con colores corporativos
- ✅ Animaciones suaves y feedback visual

### Paneles Principales

#### 1. **Panel de Configuración (Izquierda)**
- 📊 Modo de entrada:
  - Demostración (datos de ejemplo)
  - Mis datos (CSV personal)
- 📤 Subir archivo CSV
- ✓ Seleccionar tarifas a comparar
- 📅 Rango de fechas personalizable

#### 2. **Panel de Resultados (Derecha)**
Tres pestañas:

**📊 Ranking**
- Top 1, 2, 3 tarifas
- Coste anual/mensual
- Ahorros calculados
- URLs de verificación

**📈 Análisis**
- Supuestos utilizados
- Riesgos identificados
- Recomendaciones personalizadas
- Sensibilidad a cambios

**ℹ️ Detalles**
- JSON completo de resultados
- Desglose técnico
- Datos de validación

#### 3. **Métricas en Tiempo Real**
- Consumo total (kWh)
- Período de análisis (meses)
- Mejor tarifa encontrada (€)
- Ahorro máximo (€)

## 📤 Cómo Usar

### Modo Demostración (Recomendado para Probar)

1. **Abre la aplicación**: http://localhost:5000
2. **Selecciona "Demostración"** (opción por defecto)
3. **Selecciona tarifas** (2 ejemplos pre-seleccionadas)
4. **Haz clic en "⚡ Ejecutar Simulación"**
5. **Ve los resultados** en las pestañas de la derecha

**Resultado esperado**:
```
TOP 1: Electric Ireland - Smart Day & Night
Coste: 269,80€/año
Ahorro: 128,37€ vs Bord Gáis

TOP 2: Bord Gáis - Smart All Day
Coste: 398,17€/año
```

### Modo Con Tus Datos

1. **Descarga tu CSV** desde https://www.esbnetworks.ie/
   - Tu portal → Descargar datos de consumo
   - Formato: `MPRN, Meter Serial Number | Read Value | Read Type | Read Date and End Time`

2. **En la web**:
   - Selecciona "Mis datos"
   - Haz clic en "📤 Selecciona tu archivo CSV"
   - Elige tu descarga

3. **Espera validación**:
   - ✓ CSV válido
   - ✗ Rango de fechas incorrecto
   - ✗ Datos incompletos

4. **Ejecuta simulación** como en modo demo

## 🔧 API Endpoints

### `GET /api/health`
Health check del servidor.

**Respuesta**:
```json
{ "status": "ok" }
```

### `GET /api/tariffs`
Obtener lista de tarifas disponibles.

**Respuesta**:
```json
{
  "success": true,
  "tariffs": [
    {
      "supplier": "Bord Gáis",
      "plan_name": "Smart All Day",
      "source_url": "https://bordgais.ie/",
      "unit_rates_c_per_kwh_ex_vat": {...},
      ...
    }
  ]
}
```

### `POST /api/upload-csv`
Subir y procesar archivo CSV.

**Parámetros**:
- `file`: Archivo CSV (multipart/form-data)

**Respuesta**:
```json
{
  "success": true,
  "filename": "consumo.csv",
  "valid": true,
  "message": "✓ Datos válidos",
  "quality": {
    "initial_rows": 17520,
    "duplicates_removed": 4,
    "final_rows": 17516,
    "missing_intervals_imputed": 78
  }
}
```

### `POST /api/simulate`
Ejecutar simulación con datos personales.

**Parámetros**:
```json
{
  "csv_filename": "consumo.csv",
  "tariffs": [...],
  "start_month": "2026-06",
  "end_month": "2026-09"
}
```

**Respuesta**:
```json
{
  "success": true,
  "results": [
    {
      "supplier": "Bord Gáis",
      "plan_name": "Smart All Day",
      "total_cost_eur": 398.17,
      "total_consumption_kwh": 1096,
      "savings_vs_reference_eur": 0,
      ...
    }
  ],
  "report": {...}
}
```

### `POST /api/demo-simulate`
Ejecutar simulación con datos de demo.

**Parámetros**:
```json
{
  "tariffs": [...]
}
```

## 🎨 Personalizaciones

### Cambiar Colores
En `templates/index.html`, modifica `:root`:

```css
:root {
    --primary: #2563eb;        /* Azul principal */
    --primary-dark: #1e40af;
    --success: #10b981;        /* Verde */
    --warning: #f59e0b;        /* Naranja */
    --danger: #ef4444;         /* Rojo */
    ...
}
```

### Agregar Más Tarifas
Edita `config/tariffs_example.json`:

```json
{
  "supplier": "Tu Proveedor",
  "plan_name": "Tu Plan",
  "source_url": "https://...",
  "extracted_at": "2026-10-02",
  "unit_rates_c_per_kwh_ex_vat": {
    "day": 35.0,
    "night": 25.0,
    "peak": 40.0
  },
  ...
}
```

Recarga la página y aparecerán automáticamente.

## 📊 Visualizaciones

### Ranking Cards
- **#1**: Oro (mejores ahorros)
- **#2**: Plata
- **#3**: Bronce

Cada card muestra:
- Proveedor y plan
- Coste anual
- Consumo usado
- Ahorros vs referencia

### Métricas en Tiempo Real
Grid de 4 métricas que se actualiza después de cada simulación.

### Gráficos (Próxima fase)
- Línea: Costo mensual
- Barra: Comparativa de tarifas
- Pastel: Desglose por franja

## 🐛 Troubleshooting

### "Error: Cannot POST /api/demo-simulate"
- Comprueba que el servidor está corriendo: `http://localhost:5000`
- Reinicia el servidor: Ctrl+C y vuelve a ejecutar `./run_web.sh`

### "CSV file not found"
- Sube el CSV primero antes de simular
- Espera el mensaje "✓ CSV válido"

### Puerto 5000 ya en uso
```bash
# Encuentra qué proceso lo ocupa
lsof -i :5000

# O usa otro puerto:
export FLASK_PORT=5001
python3 app.py
```

Luego accede a: `http://localhost:5001`

### Interfaz lenta o sin cargar
- Limpia caché del navegador: Ctrl+Shift+Delete
- Abre en navegador privado
- Intenta otro navegador

## 🚀 Próximas Mejoras

- [ ] Gráficos interactivos (Chart.js)
- [ ] Descarga de resultados (PDF/Excel)
- [ ] Guardado de simulaciones
- [ ] Histórico de tarifas
- [ ] Comparación con otros usuarios (anónima)
- [ ] Notificaciones de cambios
- [ ] Integración con APIs de proveedores

## 📝 Estructura de Archivos

```
templates/
├── index.html          ← Interfaz web (700 líneas)
│   ├── HTML structure
│   ├── CSS styling (responsivo)
│   └── JavaScript logic

app.py                  ← Backend Flask (250 líneas)
├── GET /api/health
├── GET /api/tariffs
├── POST /api/upload-csv
├── POST /api/simulate
└── POST /api/demo-simulate

run_web.sh             ← Script de inicio

uploads/               ← CSV subidos (temporal)
```

## 📞 Soporte

Si encuentras problemas:
1. Comprueba `http://localhost:5000/api/health` → debe devolver `{"status": "ok"}`
2. Ve la consola del servidor (ver errores en backend)
3. Abre Developer Tools del navegador (F12) → Console → ver errores en cliente

## 🎓 Tecnologías

**Frontend**:
- HTML5 / CSS3
- Vanilla JavaScript (sin dependencias)
- Responsive Design

**Backend**:
- Python 3.8+
- Flask (servidor web)
- pandas (procesamiento datos)
- CORS (cross-origin requests)

**Motor**:
- `src/simulation_engine.py` (cálculos)
- `src/consumption_processor.py` (datos)
- `agents/advisor.py` (análisis)

---

**¡Listo para usar!** 🚀

Para más info: Ver README.md y CONSTRUCTION.md
