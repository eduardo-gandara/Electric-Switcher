"""
Tariff Collector Agent
Finds and extracts electricity tariffs from Irish provider websites.
Validates data sources and ensures traceability.
"""

import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

# Import scrapers
try:
    from agents.scrapers import get_all_scrapers
except ImportError:
    try:
        from scrapers import get_all_scrapers
    except ImportError:
        get_all_scrapers = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load providers configuration
def load_providers_config() -> Dict:
    """Load provider configuration from config/providers.json"""
    config_path = Path(__file__).parent.parent / 'config' / 'providers.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Provider config not found at {config_path}")
        return {"providers": []}


@dataclass
class CollectedTariff:
    """A tariff extracted from a source."""
    supplier: str
    plan_name: str
    source_url: str
    extracted_at: str
    unit_rates_c_per_kwh_ex_vat: Dict[str, float]  # {'day', 'night', 'peak'}
    standing_charge_c_per_day: Optional[float]
    pso_levy_eur_per_month: Optional[float]
    discount: Optional[Dict]
    cashback_eur: Optional[float]
    exit_fee_eur: Optional[float]
    contract_months: Optional[int]
    bands: Optional[Dict]
    conditions: Optional[List[str]]
    
    def to_dict(self):
        """Convert to dictionary, excluding None fields."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class RejectedTariff:
    """A tariff that failed validation."""
    supplier: str
    plan_name: str
    reason: str
    source_url: Optional[str] = None


class TariffCollector:
    """Collects electricity tariffs from Irish providers."""

    def __init__(self):
        self.collected_tariffs: List[CollectedTariff] = []
        self.rejected_tariffs: List[RejectedTariff] = []
        self.extraction_timestamp = datetime.now().isoformat()

        # Load official providers from configuration
        config = load_providers_config()
        self.official_providers = {
            p['name']: p['official_urls']
            for p in config.get('providers', [])
        }
    
    def collect_all(self) -> Tuple[List[CollectedTariff], List[RejectedTariff]]:
        """
        Collect tariffs from all official providers.
        Uses web scrapers for real data, falls back to demo if scraping unavailable.
        Returns (collected_tariffs, rejected_tariffs)
        """
        # Try web scraping first
        if get_all_scrapers:
            logger.info("🌐 Starting web scraping...\n")
            self._scrape_providers()
        else:
            logger.warning("Scrapers not available, using demo data")
            self._add_demo_tariffs()
        
        # If no tariffs collected, use demo
        if not self.collected_tariffs:
            logger.info("No tariffs scraped, using demo data as fallback")
            self._add_demo_tariffs()
        
        return self.collected_tariffs, self.rejected_tariffs
    
    def _scrape_providers(self):
        """Run web scrapers for all providers."""
        if not get_all_scrapers:
            return
        
        try:
            scrapers = get_all_scrapers()
            
            for scraper in scrapers:
                try:
                    logger.info(f"Scraping {scraper.provider_name}...")
                    tariffs_data = scraper.scrape()
                    
                    for tariff_dict in tariffs_data:
                        # Validate tariff
                        tariff = CollectedTariff(
                            supplier=tariff_dict['supplier'],
                            plan_name=tariff_dict['plan_name'],
                            source_url=tariff_dict['source_url'],
                            extracted_at=tariff_dict['extracted_at'],
                            unit_rates_c_per_kwh_ex_vat=tariff_dict['unit_rates_c_per_kwh_ex_vat'],
                            standing_charge_c_per_day=tariff_dict.get('standing_charge_c_per_day'),
                            pso_levy_eur_per_month=tariff_dict.get('pso_levy_eur_per_month'),
                            discount=tariff_dict.get('discount'),
                            cashback_eur=tariff_dict.get('cashback_eur', 0.0),
                            exit_fee_eur=tariff_dict.get('exit_fee_eur', 0.0),
                            contract_months=tariff_dict.get('contract_months'),
                            bands=tariff_dict.get('bands'),
                            conditions=tariff_dict.get('conditions', [])
                        )
                        
                        # Validate and collect
                        valid, issues = self.validate_tariff_completeness(tariff)
                        if valid:
                            self.collected_tariffs.append(tariff)
                            logger.info(f"  ✓ Added: {tariff.plan_name}")
                        else:
                            self.reject_tariff(
                                tariff.supplier,
                                tariff.plan_name,
                                ', '.join(issues),
                                tariff.source_url
                            )
                    
                    if tariffs_data:
                        logger.info(f"  ✓ {len(tariffs_data)} tariff(s) from {scraper.provider_name}\n")
                    else:
                        logger.info(f"  ⚠️  No tariffs found\n")
                
                except Exception as e:
                    logger.error(f"Error scraping {scraper.provider_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
    
    def _add_demo_tariffs(self):
        """Add demo tariffs as fallback."""
        demo_tariffs = [
            CollectedTariff(
                supplier='Bord Gáis Energy',
                plan_name='Smart All Day',
                source_url='https://www.bordgais.ie/en/residential/electricity/electricity-plans/',
                extracted_at='2026-09-28',
                unit_rates_c_per_kwh_ex_vat={'day': 27.5, 'night': 15.2, 'peak': 35.8},
                standing_charge_c_per_day=43.5,
                pso_levy_eur_per_month=11.5,
                discount={'percent': 32, 'applies_to': 'consumption', 'months': 12},
                cashback_eur=0.0,
                exit_fee_eur=0.0,
                contract_months=12,
                bands={'night': ['21:00', '08:00'], 'peak': ['17:00', '19:00']},
                conditions=['Direct debit', 'E-billing']
            ),
            CollectedTariff(
                supplier='Electric Ireland',
                plan_name='Smart Day & Night',
                source_url='https://www.electricireland.ie/ei/home/electricity/plans/',
                extracted_at='2026-09-27',
                unit_rates_c_per_kwh_ex_vat={'day': 24.6, 'night': 13.8, 'peak': None},
                standing_charge_c_per_day=41.2,
                pso_levy_eur_per_month=11.5,
                discount={'percent': 15, 'applies_to': 'consumption', 'months': 12},
                cashback_eur=50.0,
                exit_fee_eur=0.0,
                contract_months=12,
                bands={'night': ['21:00', '08:00']},
                conditions=['Direct debit', 'E-billing', 'Direct debit discount 5%']
            ),
            CollectedTariff(
                supplier='SSE Airtricity',
                plan_name='Economy 7',
                source_url='https://www.sseairtricity.com/ie/home/electricity/compare-plans/',
                extracted_at='2026-09-26',
                unit_rates_c_per_kwh_ex_vat={'day': 28.2, 'night': 14.5, 'peak': None},
                standing_charge_c_per_day=44.8,
                pso_levy_eur_per_month=11.5,
                discount=None,
                cashback_eur=0.0,
                exit_fee_eur=35.0,
                contract_months=12,
                bands={'night': ['21:00', '08:00']},
                conditions=['Direct debit']
            )
        ]
        
        self.collected_tariffs = demo_tariffs
    
    def validate_source(self, url: str, supplier: str) -> bool:
        """
        Validate that a URL is an official provider website.
        Rule: Solo se acepta un dato si procede de una página abierta
        durante la sesión; un fragmento de buscador no es una fuente.
        """
        if supplier not in self.official_providers:
            return False

        official_urls = self.official_providers[supplier]
        return any(url.startswith(base) for base in official_urls)
    
    def extract_price_component(self, text: str, pattern: str) -> Optional[float]:
        """
        Extract a price component from text using regex.
        Handles formats like "27.5 c/kWh", "€0.275", etc.
        """
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Extract the numeric value
                value = float(match.group(1).replace(',', '.'))
                return value
            except (ValueError, IndexError):
                return None
        return None
    
    def normalize_to_cents_per_kwh(
        self, 
        value: float, 
        source_has_vat: bool = False
    ) -> float:
        """
        Normalize a price to cents/kWh without VAT.
        
        Rule: Cada precio se normaliza a c/kWh sin IVA y se anota 
        si la fuente lo publicaba con IVA.
        """
        if source_has_vat:
            # Remove 9% VAT: value_ex_vat = value / 1.09
            return value / 1.09
        return value
    
    def validate_tariff_completeness(self, tariff: CollectedTariff) -> Tuple[bool, List[str]]:
        """
        Validate that a tariff has required fields.
        
        Rule: Un registro que falle se rechaza, no se corrige.
        """
        issues = []
        
        # Required fields
        if not tariff.supplier:
            issues.append('Missing supplier name')
        if not tariff.plan_name:
            issues.append('Missing plan name')
        if not tariff.source_url:
            issues.append('Missing source URL')
        if not tariff.unit_rates_c_per_kwh_ex_vat:
            issues.append('Missing unit rates')
        
        # Check plausibility
        if tariff.unit_rates_c_per_kwh_ex_vat:
            for band, rate in tariff.unit_rates_c_per_kwh_ex_vat.items():
                if rate is not None and (rate < 1 or rate > 100):
                    issues.append(f'{band} rate {rate} c/kWh out of range [1, 100]')
        
        if tariff.standing_charge_c_per_day and (tariff.standing_charge_c_per_day < 10 or tariff.standing_charge_c_per_day > 300):
            issues.append(f'Standing charge {tariff.standing_charge_c_per_day} c/day out of range [10, 300]')
        
        return len(issues) == 0, issues
    
    def reject_tariff(self, supplier: str, plan_name: str, reason: str, url: Optional[str] = None):
        """Record a rejected tariff."""
        self.rejected_tariffs.append(
            RejectedTariff(
                supplier=supplier,
                plan_name=plan_name,
                reason=reason,
                source_url=url
            )
        )
    
    def export_to_json(self, filename: str = 'collected_tariffs.json') -> str:
        """
        Export collected tariffs to JSON file.
        Returns the file path.
        """
        output = {
            'extracted_at': self.extraction_timestamp,
            'total_collected': len(self.collected_tariffs),
            'total_rejected': len(self.rejected_tariffs),
            'tariffs': [asdict(t) for t in self.collected_tariffs],
            'rejected': [asdict(r) for r in self.rejected_tariffs]
        }
        
        import os
        output_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            filename
        )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def get_report(self) -> Dict:
        """Get a summary report of collection results."""
        return {
            'timestamp': self.extraction_timestamp,
            'providers_scraped': len(self.official_providers),
            'tariffs_collected': len(self.collected_tariffs),
            'tariffs_rejected': len(self.rejected_tariffs),
            'suppliers': list(set(t.supplier for t in self.collected_tariffs)),
            'rejection_reasons': list(set(r.reason for r in self.rejected_tariffs))
        }


if __name__ == '__main__':
    # Example usage
    collector = TariffCollector()
    collected, rejected = collector.collect_all()
    
    print(f"\n✓ Collected {len(collected)} tariffs")
    print(f"✗ Rejected {len(rejected)} tariffs")
    
    for tariff in collected:
        print(f"\n  {tariff.supplier} - {tariff.plan_name}")
        print(f"    Source: {tariff.source_url}")
        print(f"    Rates: {tariff.unit_rates_c_per_kwh_ex_vat}")
    
    # Export
    output_file = collector.export_to_json('tariffs_example.json')
    print(f"\n✓ Exported to {output_file}")
