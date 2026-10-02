#!/usr/bin/env python3
"""
Tariff Collector CLI
Collect electricity tariffs from Irish providers.

Usage:
    python3 collect_tariffs.py                    # Collect and display
    python3 collect_tariffs.py --export           # Export to JSON
    python3 collect_tariffs.py --report           # Show collection report
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.tariff_collector import TariffCollector


def main():
    parser = argparse.ArgumentParser(
        description='Collect electricity tariffs from Irish providers'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export collected tariffs to JSON file'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Show collection report only'
    )
    parser.add_argument(
        '--output',
        default='tariffs_example.json',
        help='Output JSON filename (default: tariffs_example.json)'
    )
    
    args = parser.parse_args()
    
    # Create collector and run
    print("🔍 Collecting electricity tariffs from Irish providers...\n")
    collector = TariffCollector()
    collected, rejected = collector.collect_all()
    
    # Show report
    report = collector.get_report()
    print(f"✓ Collection completed at {report['timestamp']}")
    print(f"  Providers scraped: {report['providers_scraped']}")
    print(f"  Tariffs collected: {report['tariffs_collected']}")
    print(f"  Tariffs rejected: {report['tariffs_rejected']}")
    
    if args.report:
        return 0
    
    # Show collected tariffs
    if collected:
        print(f"\n📋 Collected Tariffs ({len(collected)}):\n")
        for i, tariff in enumerate(collected, 1):
            print(f"  {i}. {tariff.supplier} - {tariff.plan_name}")
            print(f"     Source: {tariff.source_url}")
            print(f"     Extracted: {tariff.extracted_at}")
            print(f"     Rates: {tariff.unit_rates_c_per_kwh_ex_vat}")
            if tariff.standing_charge_c_per_day:
                print(f"     Standing charge: {tariff.standing_charge_c_per_day} c/day")
            if tariff.discount:
                print(f"     Discount: {tariff.discount}")
            print()
    
    # Show rejected tariffs
    if rejected:
        print(f"\n⚠️  Rejected Tariffs ({len(rejected)}):\n")
        for i, tariff in enumerate(rejected, 1):
            print(f"  {i}. {tariff.supplier} - {tariff.plan_name}")
            print(f"     Reason: {tariff.reason}")
            if tariff.source_url:
                print(f"     Source: {tariff.source_url}")
            print()
    
    # Export if requested
    if args.export:
        output_file = collector.export_to_json(args.output)
        print(f"✓ Exported to {output_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
