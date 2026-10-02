# Web Scraping Implementation

El sistema de recopilación de tarifas incluye scrapers reales para extraer precios de los sitios web de los proveedores.

## Arquitectura

```
TariffCollector (agente principal)
├── BordGaisScraper
├── ElectricIrelandScraper
├── SSEAirticityScraper
├── EnergiaIrelandScraper
├── PinergyScraper
└── EvokeEnergyScraper
```

Cada scraper es independiente y:
- Hereda de `BaseScraper`
- Implementa método `scrape()`
- Retorna lista de tarifas extraídas
- Maneja errores gracefully

## Flujo de Recopilación

```
1. TariffCollector.collect_all()
   ├─ Intenta web scraping con get_all_scrapers()
   │  ├─ BordGaisScraper.scrape() → Lista tarifas
   │  ├─ ElectricIrelandScraper.scrape() → Lista tarifas
   │  └─ ... (otros scrapers)
   │
   ├─ Valida cada tarifa extraída
   ├─ Rechaza si falta datos o están fuera de rango
   │
   └─ Si no hay resultados, usa datos demo como fallback
```

## Uso

### Desde CLI

```bash
# Ejecutar scrapers (fallback a demo si falla)
python3 collect_tariffs.py

# Ver solo el reporte
python3 collect_tariffs.py --report

# Exportar a JSON
python3 collect_tariffs.py --export
```

### Desde Python

```python
from agents.tariff_collector import TariffCollector

collector = TariffCollector()
collected, rejected = collector.collect_all()

# Usa web scraping si está disponible
# Fallback a demo si el scraping falla
```

### Desde API

```bash
POST /api/collect-tariffs

# Respuesta:
{
  "success": true,
  "report": { ... },
  "tariffs": [ ... ],
  "rejected": [],
  "exported_to": "/path/to/tariffs_example.json"
}
```

## Cómo Personalizar Scrapers

### 1. Inspeccionar el HTML del sitio

```bash
# Guardar HTML para inspeccionar
curl -s https://www.bordgais.ie/en/residential/electricity/electricity-plans/ > page.html

# Abrir en navegador o editor
open page.html
```

### 2. Identificar estructura HTML

Busca elementos como:
- **Plan names**: `<h2>`, `<h3>`, `<div class="plan-name">`
- **Precios**: `<span class="price">`, `<div class="rate">`
- **Cargo fijo**: `<span class="standing-charge">`
- **Descuentos**: `<div class="discount">`

### 3. Actualizar scraper

Edita `/agents/scrapers.py` y modifica el método `scrape()` del scraper:

```python
class BordGaisScraper(BaseScraper):
    def scrape(self) -> List[Dict]:
        url = 'https://...'
        soup = self.fetch_page(url)
        
        # Buscar contenedores de planes
        plan_containers = soup.find_all('div', class_='plan')
        
        for container in plan_containers:
            # Extraer nombre
            name = container.find('h2').text
            
            # Extraer precios
            price_text = container.find('span', class_='price').text
            day_rate = self.extract_price(price_text)
            
            # Crear tarifa
            tariff = {
                'supplier': self.provider_name,
                'plan_name': name,
                'source_url': url,
                'extracted_at': self.extracted_at,
                'unit_rates_c_per_kwh_ex_vat': {'day': day_rate, ...},
                # ... otros campos
            }
            tariffs.append(tariff)
        
        return tariffs
```

## Métodos Útiles de BaseScraper

### fetch_page(url)
Descarga y parsea una página web.

```python
soup = self.fetch_page('https://example.com/page')
if soup:
    # Procesar soup
else:
    # Error (log ya escrito)
```

### extract_price(text)
Extrae un número de precio de texto.

```python
price = self.extract_price("27.5 c/kWh")  # → 27.5
price = self.extract_price("€0.275")      # → 0.275
price = self.extract_price("27,5")        # → 27.5
```

## Validaciones Automáticas

Después de scrapear, cada tarifa se valida:

```python
valid, issues = collector.validate_tariff_completeness(tariff)

if not valid:
    # Rechazado - ejemplos de issues:
    # - "Missing supplier name"
    # - "day rate 0.5 c/kWh out of range [1, 100]"
    # - "Standing charge 5.0 c/day out of range [10, 300]"
```

## Rangos Válidos

| Campo | Rango | Notas |
|-------|-------|-------|
| Precio (c/kWh) | 1-100 | Por banda (día, noche, pico) |
| Cargo fijo (c/día) | 10-300 | Línea típica 30-50 |
| Descuento (%) | 0-100 | Primer año |
| Exit fee (€) | 0-200 | Típico 0-50 |
| PSO levy (€/mes) | 0-50 | Típico 10-15 |

## Manejo de Errores

### Sin conexión

```
HTTPConnectionError → Warning log → No tariffs → Demo fallback
```

### Sitio no disponible (404)

```
404 Client Error → Warning log → No tariffs → Demo fallback
```

### SSL/TLS error

```
SSLError → Warning log → No tariffs → Demo fallback
```

### HTML no esperado

```
ParseError → Warning log → Tarifa rechazada → Continuar con próximo
```

## Testing

### Simular scraping

```python
# Crear mock scraper
class MockBordGaisScraper(BordGaisScraper):
    def scrape(self):
        # Retorna tarifas hardcoded
        return [{...}, {...}]

# Usar en collector
from agents.tariff_collector import TariffCollector
collector = TariffCollector()
# ... etc
```

### Ver logs detallados

```bash
# Con logging DEBUG
import logging
logging.getLogger().setLevel(logging.DEBUG)

python3 collect_tariffs.py
```

## Próximos Pasos

1. **Actualizar URLs** si cambian en proveedores reales
2. **Mejorar selectores CSS** basado en inspección HTML real
3. **Agregar Selenium** para sitios JavaScript-heavy
4. **Implementar retry logic** para conexiones inestables
5. **Scheduler diario** para actualizar tarifas automáticamente

## Ejemplo Real

Para Bord Gáis, el HTML podría verse así:

```html
<div class="plan-card">
  <h2 class="plan-name">Smart All Day</h2>
  <div class="pricing">
    <span class="price">27.5</span>
    <span class="unit">c/kWh</span>
  </div>
  <div class="standing-charge">
    Standing: <span>43.5</span>c/day
  </div>
  <div class="discount">
    Discount: <span>32%</span>
  </div>
</div>
```

El scraper lo extraería así:

```python
name = "Smart All Day"
day_rate = 27.5
standing_charge = 43.5
discount = {"percent": 32, "applies_to": "consumption", "months": 12}
```

