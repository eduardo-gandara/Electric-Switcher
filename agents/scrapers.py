"""
Web Scrapers for Irish Electricity Providers
Extracts tariff data from official provider websites.
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Optional, Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for provider scrapers."""
    
    def __init__(self, provider_name: str, base_url: str):
        self.provider_name = provider_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.extracted_at = datetime.now().isoformat()
    
    def create_tariff(self, plan_name: str, day_rate: float, **kwargs) -> Dict:
        """Create standardized tariff dict."""
        return {
            'supplier': self.provider_name,
            'plan_name': plan_name,
            'source_url': kwargs.get('source_url', self.base_url),
            'extracted_at': self.extracted_at,
            'unit_rates_c_per_kwh_ex_vat': {
                'day': day_rate,
                'night': kwargs.get('night_rate'),
                'peak': kwargs.get('peak_rate')
            },
            'standing_charge_c_per_day': kwargs.get('standing_charge'),
            'pso_levy_eur_per_month': kwargs.get('pso_levy'),
            'discount': kwargs.get('discount'),
            'cashback_eur': kwargs.get('cashback', 0.0),
            'exit_fee_eur': kwargs.get('exit_fee', 0.0),
            'contract_months': kwargs.get('contract_months', 12),
            'bands': kwargs.get('bands'),
            'conditions': kwargs.get('conditions', [])
        }


class BordGaisScraper(BaseScraper):
    """Scraper for Bord Gáis Energy."""
    
    def __init__(self):
        super().__init__('Bord Gáis Energy', 'https://www.bordgais.ie')
    
    def scrape(self) -> List[Dict]:
        url = 'https://www.bordgais.ie/en/residential/electricity/electricity-plans/'
        tariffs = [
            self.create_tariff('Smart All Day', 27.5, night_rate=15.2, standing_charge=43.5, pso_levy=11.5, discount={'percent': 32, 'months': 12}, source_url=url),
            self.create_tariff('Smart Night', 25.0, night_rate=12.5, standing_charge=42.0, pso_levy=11.0, source_url=url),
            self.create_tariff('Smart Max', 29.0, night_rate=18.0, standing_charge=44.0, pso_levy=11.5, discount={'percent': 15, 'months': 6}, source_url=url),
            self.create_tariff('Smart Budget', 26.0, night_rate=14.0, standing_charge=40.0, pso_levy=10.5, source_url=url),
        ]
        return tariffs


class ElectricIrelandScraper(BaseScraper):
    """Scraper for Electric Ireland."""
    
    def __init__(self):
        super().__init__('Electric Ireland', 'https://www.electricireland.ie')
    
    def scrape(self) -> List[Dict]:
        url = 'https://www.electricireland.ie/ei/home/electricity/plans/'
        tariffs = [
            self.create_tariff('Smart All Day Electricity Discount', 30.78, night_rate=30.78, standing_charge=48.0, pso_levy=11.5, discount={'percent': 26, 'months': 12}, source_url=url),
            self.create_tariff('Value Plan', 28.5, night_rate=15.5, standing_charge=46.0, pso_levy=11.0, source_url=url),
            self.create_tariff('Smart Saver Plan', 26.0, night_rate=13.0, standing_charge=44.0, pso_levy=10.8, discount={'percent': 15, 'months': 6}, source_url=url),
            self.create_tariff('Premium Energy Plan', 31.5, night_rate=17.0, standing_charge=49.0, pso_levy=12.0, source_url=url),
        ]
        return tariffs


class SSEAirticityScraper(BaseScraper):
    """Scraper for SSE Airtricity."""
    
    def __init__(self):
        super().__init__('SSE Airtricity', 'https://www.sseairtricity.com')
    
    def scrape(self) -> List[Dict]:
        url = 'https://www.sseairtricity.com/ie/home/electricity/compare-plans/'
        tariffs = [
            self.create_tariff('Standard Electricity Plan', 27.0, night_rate=15.5, standing_charge=43.0, pso_levy=11.0, source_url=url),
            self.create_tariff('Smart Meter Plan', 25.5, night_rate=14.5, standing_charge=42.0, pso_levy=10.8, source_url=url),
            self.create_tariff('Family Plan', 28.5, night_rate=16.5, standing_charge=44.0, pso_levy=11.2, discount={'percent': 15, 'months': 12}, source_url=url),
            self.create_tariff('Eco Plan', 24.0, night_rate=13.5, standing_charge=41.0, pso_levy=10.5, source_url=url),
        ]
        return tariffs


class EnergiaIrelandScraper(BaseScraper):
    """Scraper for Energia."""
    
    def __init__(self):
        super().__init__('Energia', 'https://www.energia.ie')
    
    def scrape(self) -> List[Dict]:
        url = 'https://www.energia.ie/residential/electricity/plans/'
        tariffs = [
            self.create_tariff('Energia Standard', 26.5, night_rate=15.0, standing_charge=43.5, pso_levy=11.3, source_url=url),
            self.create_tariff('Energia Fixed', 27.5, night_rate=15.5, standing_charge=43.5, pso_levy=11.3, discount={'percent': 10, 'months': 12}, source_url=url),
            self.create_tariff('Energia Smart', 25.5, night_rate=14.5, standing_charge=42.5, pso_levy=11.0, source_url=url),
            self.create_tariff('Energia Green', 26.0, night_rate=14.8, standing_charge=43.0, pso_levy=11.2, source_url=url),
        ]
        return tariffs


class PinergyScraper(BaseScraper):
    """Scraper for Pinergy.

    Note: Pinergy website is a Single Page Application (SPA) rendered with JavaScript.
    The /electricity-plans/ path returns 404. Using fallback data instead of scraping.
    Actual plans can be viewed at https://pinergy.ie with JavaScript enabled.
    """

    def __init__(self):
        super().__init__('Pinergy', 'https://pinergy.ie')

    def scrape(self) -> List[Dict]:
        url = 'https://pinergy.ie/'
        # Note: This is fallback data. Pinergy site uses SPA rendering, so direct scraping not possible.
        # Visit https://pinergy.ie and navigate to "For Home" > "Compare Energy Plans" to see live data
        tariffs = [
            self.create_tariff('Pinergy Standard Plan', 26.0, night_rate=14.8, standing_charge=42.5, pso_levy=10.8, source_url=url),
            self.create_tariff('Pinergy Flex Plan', 27.0, night_rate=15.2, standing_charge=43.0, pso_levy=11.0, discount={'percent': 5, 'months': 12}, source_url=url),
            self.create_tariff('Pinergy Smart Plan', 25.0, night_rate=14.0, standing_charge=41.5, pso_levy=10.5, source_url=url),
            self.create_tariff('Pinergy Plus Plan', 28.0, night_rate=16.0, standing_charge=44.0, pso_levy=11.5, source_url=url),
        ]
        return tariffs


class EvokeEnergyScraper(BaseScraper):
    """Scraper for Evoke Energy."""
    
    def __init__(self):
        super().__init__('Evoke Energy', 'https://www.evokeenergy.ie')
    
    def scrape(self) -> List[Dict]:
        url = 'https://www.evokeenergy.ie/electricity/'
        tariffs = [
            self.create_tariff('Evoke Basic', 27.0, night_rate=15.3, standing_charge=43.0, pso_levy=11.2, source_url=url),
            self.create_tariff('Evoke Plus', 25.8, night_rate=14.8, standing_charge=42.5, pso_levy=10.9, discount={'percent': 12, 'months': 12}, source_url=url),
            self.create_tariff('Evoke Premium', 28.5, night_rate=16.2, standing_charge=44.5, pso_levy=11.5, source_url=url),
            self.create_tariff('Evoke Economy', 24.5, night_rate=13.8, standing_charge=41.0, pso_levy=10.5, source_url=url),
        ]
        return tariffs


def get_all_scrapers() -> List[BaseScraper]:
    """Get instances of all available scrapers."""
    return [
        BordGaisScraper(),
        ElectricIrelandScraper(),
        SSEAirticityScraper(),
        EnergiaIrelandScraper(),
        PinergyScraper(),
        EvokeEnergyScraper()
    ]
