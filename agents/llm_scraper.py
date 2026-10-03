"""
LLM-based Tariff Scrapers using Google Gemini
Extracts tariff data by asking Gemini to analyze provider URLs and extract structured data.
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from agents.scrapers import load_providers_config, get_provider_config

try:
    import google.generativeai as genai
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMScraperBase:
    """Base class for LLM-based scrapers using Google Gemini"""

    def __init__(self, provider_name: str, provider_config: Optional[Dict] = None):
        self.provider_name = provider_name
        self.provider_config = provider_config or get_provider_config(provider_name)

        # Initialize Gemini
        if LLM_AVAILABLE:
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                # Use gemini-3.8-flash (latest recommended model)
                self.model = None
                try:
                    self.model = genai.GenerativeModel('models/gemini-3.8-flash')
                    logger.info(f"✅ Using model: gemini-3.8-flash")
                except Exception as e:
                    logger.warning(f"gemini-2.5-flash not available: {e}, falling back to first available model...")
                    try:
                        models = genai.list_models()
                        for m in models:
                            if 'generateContent' in m.supported_generation_methods:
                                self.model = genai.GenerativeModel(m.name)
                                logger.info(f"✅ Using model: {m.name}")
                                break
                    except Exception as e2:
                        logger.error(f"Error selecting model: {e2}")
                        self.model = None
            else:
                self.model = None
                logger.warning("GEMINI_API_KEY not configured")
        else:
            self.model = None

        self.extraction_timestamp = datetime.now().isoformat()

    def scrape(self) -> List[Dict]:
        """Scrape tariff data using Gemini LLM"""
        if not LLM_AVAILABLE or not self.model:
            logger.warning(f"Gemini model not available for {self.provider_name}")
            return []

        if not self.provider_config:
            logger.warning(f"No configuration found for {self.provider_name}")
            return []

        try:
            urls = self.provider_config.get('official_urls', [])
            if not urls:
                logger.warning(f"No URLs found for {self.provider_name}")
                return []

            url = urls[0]  # Use first URL
            logger.info(f"🤖 Using Gemini to extract {self.provider_name} from {url}")

            # Ask Gemini to extract tariff data
            tariffs = self._extract_tariffs_with_llm(url)

            if tariffs:
                logger.info(f"✅ Successfully extracted {len(tariffs)} real tariffs from {self.provider_name} via Gemini")
            else:
                logger.info(f"⚠️  No tariffs found for {self.provider_name}")

            return tariffs

        except Exception as e:
            logger.error(f"Error in Gemini scraping for {self.provider_name}: {e}")
            return []

    def _extract_tariffs_with_llm(self, url: str) -> List[Dict]:
        """Use Gemini to extract tariff data from URL"""
        prompt = f"""You are a data extraction expert. Analyze the electricity provider website: {url}

Your task is to extract ELECTRICITY-ONLY tariff data for {self.provider_name} and return it as a JSON array.

IMPORTANT: Extract ONLY electricity tariffs, NOT combined electricity+gas packages.

For each electricity tariff plan, ONLY extract if it has:
- A clear plan name
- Unit rates for electricity (must include at least 'day' rate)
- A standing charge amount
- Valid financial data

Extract these fields:
- plan_name: the name of the tariff plan
- unit_rates_c_per_kwh_ex_vat: object with 'day', 'night', 'peak' rates (in c/kWh, excluding VAT). Must have at least 'day' rate.
- standing_charge_c_per_day: daily standing charge in cents
- pso_levy_eur_per_month: PSO levy in EUR per month (if available)
- discount: object with 'percent' and 'applies_to' fields (optional)
- cashback_eur: cashback amount in EUR (optional)
- exit_fee_eur: exit fee in EUR (optional)
- contract_months: contract length in months (optional)

Return ONLY a valid JSON array. Example format:
[
  {{
    "plan_name": "Smart Day & Night",
    "unit_rates_c_per_kwh_ex_vat": {{"day": 24.6, "night": 13.8, "peak": null}},
    "standing_charge_c_per_day": 41.2,
    "pso_levy_eur_per_month": 11.5,
    "discount": {{"percent": 15, "applies_to": "consumption", "months": 12}},
    "cashback_eur": 50.0,
    "exit_fee_eur": 0.0,
    "contract_months": 12
  }}
]

Extract only real, complete tariffs that you can verify on the website. Skip any tariffs with missing unit rates or incomplete pricing information.
Return ONLY the JSON array, no other text."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Log the raw response for debugging (first 500 chars)
            logger.info(f"Gemini response for {self.provider_name}: {response_text[:500]}")

            # Try to extract JSON from response - handle markdown code blocks
            json_text = response_text
            if '```json' in json_text:
                # Extract JSON from markdown code block
                json_text = json_text.split('```json')[1].split('```')[0].strip()
            elif '```' in json_text:
                # Extract from generic code block
                json_text = json_text.split('```')[1].split('```')[0].strip()

            # Try to parse JSON
            tariff_data = json.loads(json_text)
            if not isinstance(tariff_data, list):
                logger.warning(f"Expected list, got {type(tariff_data)}")
                return []

            # Enrich with metadata
            enriched_tariffs = []
            for tariff in tariff_data:
                enriched = {
                    "supplier": self.provider_name,
                    "source_url": url,
                    "extracted_at": self.extraction_timestamp,
                    **tariff
                }
                enriched_tariffs.append(enriched)

            return enriched_tariffs

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error calling Gemini for {self.provider_name}: {e}")
            return []


def get_llm_scrapers() -> List[LLMScraperBase]:
    """Get LLM scrapers for all configured providers"""
    config = load_providers_config()
    scrapers = []

    for provider in config.get('providers', []):
        scraper = LLMScraperBase(
            provider_name=provider['name'],
            provider_config=provider
        )
        scrapers.append(scraper)

    return scrapers
