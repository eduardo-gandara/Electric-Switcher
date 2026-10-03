"""
Scenario Generator - Phase 4
Converts scenario parameters into consumption profiles
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScenarioProfileGenerator:
    """Generates consumption profiles for scenarios (EV, heat pump, solar, etc.)"""

    def __init__(self):
        pass

    def generate_electric_vehicle_profile(
        self,
        start_month: str,  # '2026-06'
        end_month: str,
        annual_km: float,
        consumption_kwh_per_100km: float,
        charging_hours  # '20:00-08:00' or '09:00-17:00'
    ) -> pd.DataFrame:
        """
        Generate consumption profile for electric vehicle charging.

        Args:
            start_month: Start month (YYYY-MM)
            end_month: End month (YYYY-MM)
            annual_km: Annual kilometers
            consumption_kwh_per_100km: Consumption rate
            charging_hours: Time range for charging (e.g., '20:00-08:00')

        Returns:
            DataFrame with columns [timestamp, kwh, band]
        """
        # Parse charging hours
        try:
            charging_hours = str(charging_hours)  # Ensure it's a string
            start_hour_str, end_hour_str = charging_hours.split('-')
            start_hour = int(start_hour_str.split(':')[0])
            end_hour = int(end_hour_str.split(':')[0])
        except:
            start_hour, end_hour = 20, 8  # Default: night

        # Calculate monthly consumption
        start = pd.Period(start_month, 'M')
        end = pd.Period(end_month, 'M')
        months = pd.period_range(start, end, freq='M')
        months_count = len(months)

        monthly_kwh = annual_km / 100 * consumption_kwh_per_100km / 12

        # Generate 30-minute intervals
        data = []

        for month in months:
            month_start = month.to_timestamp()
            days_in_month = month.days_in_month
            intervals_per_day = 48  # 30-minute intervals

            # Distribute consumption throughout the month
            kwh_per_interval = monthly_kwh / (days_in_month * intervals_per_day)

            for day in range(days_in_month):
                day_date = month_start + timedelta(days=day)

                for interval in range(intervals_per_day):
                    timestamp = day_date + timedelta(minutes=interval * 30)
                    hour = timestamp.hour

                    # Determine if this interval is in charging window
                    if start_hour < end_hour:
                        # Normal range (e.g., 09:00-17:00)
                        in_charging_window = start_hour <= hour < end_hour
                    else:
                        # Overnight range (e.g., 20:00-08:00)
                        in_charging_window = hour >= start_hour or hour < end_hour

                    # Only add consumption if in charging window
                    if in_charging_window:
                        data.append({
                            'timestamp': timestamp,
                            'kwh': kwh_per_interval,
                            'band': 'night' if (hour >= 21 or hour < 8) else 'day'
                        })

        df = pd.DataFrame(data)
        logger.info(
            f"Generated EV profile: {len(df)} intervals, "
            f"{df['kwh'].sum():.0f} kWh total"
        )
        return df

    def generate_heat_pump_profile(
        self,
        start_month: str,
        end_month: str,
        annual_heating_kwh: float,
        heating_months_str  # '10,11,12,1,2,3,4' or list
    ) -> pd.DataFrame:
        """
        Generate consumption profile for heat pump.

        Args:
            start_month: Start month (YYYY-MM)
            end_month: End month (YYYY-MM)
            annual_heating_kwh: Annual heating consumption
            heating_months_str: Comma-separated months (e.g., '10,11,12,1,2,3,4')

        Returns:
            DataFrame with columns [timestamp, kwh, band]
        """
        # Handle both string and number inputs
        if isinstance(heating_months_str, (int, float)):
            heating_months_str = str(int(heating_months_str))

        heating_months = set(int(m.strip()) for m in str(heating_months_str).split(','))

        start = pd.Period(start_month, 'M')
        end = pd.Period(end_month, 'M')
        months = pd.period_range(start, end, freq='M')

        data = []

        for month in months:
            month_num = month.month
            if month_num not in heating_months:
                continue  # Skip non-heating months

            month_start = month.to_timestamp()
            days_in_month = month.days_in_month
            intervals_per_day = 48

            # Distribute consumption throughout the month
            monthly_kwh = annual_heating_kwh / len(heating_months)
            kwh_per_interval = monthly_kwh / (days_in_month * intervals_per_day)

            for day in range(days_in_month):
                day_date = month_start + timedelta(days=day)

                for interval in range(intervals_per_day):
                    timestamp = day_date + timedelta(minutes=interval * 30)
                    hour = timestamp.hour

                    data.append({
                        'timestamp': timestamp,
                        'kwh': kwh_per_interval,
                        'band': 'night' if (hour >= 21 or hour < 8) else 'day'
                    })

        df = pd.DataFrame(data)
        logger.info(
            f"Generated heat pump profile: {len(df)} intervals, "
            f"{df['kwh'].sum():.0f} kWh total"
        )
        return df

    def generate_solar_panels_profile(
        self,
        start_month: str,
        end_month: str,
        annual_production_kwh: float,
        peak_hours  # '08:00-16:00'
    ) -> pd.DataFrame:
        """
        Generate negative consumption (production) profile for solar panels.

        Args:
            start_month: Start month (YYYY-MM)
            end_month: End month (YYYY-MM)
            annual_production_kwh: Annual production
            peak_hours: Peak production hours (e.g., '08:00-16:00')

        Returns:
            DataFrame with columns [timestamp, kwh, band]
        """
        try:
            peak_hours = str(peak_hours)  # Ensure it's a string
            start_hour_str, end_hour_str = peak_hours.split('-')
            peak_start = int(start_hour_str.split(':')[0])
            peak_end = int(end_hour_str.split(':')[0])
        except:
            peak_start, peak_end = 8, 16

        start = pd.Period(start_month, 'M')
        end = pd.Period(end_month, 'M')
        months = pd.period_range(start, end, freq='M')

        data = []

        for month in months:
            month_start = month.to_timestamp()
            days_in_month = month.days_in_month
            intervals_per_day = 48

            monthly_kwh = annual_production_kwh / 12
            kwh_per_interval = monthly_kwh / (days_in_month * intervals_per_day)

            for day in range(days_in_month):
                day_date = month_start + timedelta(days=day)

                for interval in range(intervals_per_day):
                    timestamp = day_date + timedelta(minutes=interval * 30)
                    hour = timestamp.hour

                    # Only during peak hours
                    if peak_start <= hour < peak_end:
                        data.append({
                            'timestamp': timestamp,
                            'kwh': -kwh_per_interval,  # Negative = production
                            'band': 'day'
                        })

        df = pd.DataFrame(data)
        logger.info(
            f"Generated solar profile: {len(df)} intervals, "
            f"{-df['kwh'].sum():.0f} kWh total production"
        )
        return df

    def generate_remote_work_profile(
        self,
        start_month: str,
        end_month: str,
        base_consumption_kwh: float,
        additional_consumption_percent: float,
        working_days_per_week: int
    ) -> pd.DataFrame:
        """
        Generate additional consumption profile for remote work.

        Args:
            start_month: Start month (YYYY-MM)
            end_month: End month (YYYY-MM)
            base_consumption_kwh: Base annual consumption (for percentage calculation)
            additional_consumption_percent: Additional % during work hours
            working_days_per_week: Days per week working from home

        Returns:
            DataFrame with columns [timestamp, kwh, band]
        """
        start = pd.Period(start_month, 'M')
        end = pd.Period(end_month, 'M')
        months = pd.period_range(start, end, freq='M')
        months_count = len(months)

        # Calculate additional daily consumption
        annual_additional = base_consumption_kwh * (additional_consumption_percent / 100)
        daily_additional = annual_additional / 365

        data = []

        for month in months:
            month_start = month.to_timestamp()
            days_in_month = month.days_in_month

            for day in range(days_in_month):
                day_date = month_start + timedelta(days=day)
                weekday = day_date.weekday()  # 0=Monday, 4=Friday

                # Only on working days
                if weekday >= 5:  # Weekend
                    continue

                if working_days_per_week < 5:
                    # If not all weekdays, distribute randomly
                    if weekday >= working_days_per_week:
                        continue

                intervals_per_day = 48
                kwh_per_interval = daily_additional / intervals_per_day

                for interval in range(intervals_per_day):
                    timestamp = day_date + timedelta(minutes=interval * 30)
                    hour = timestamp.hour

                    # Consume during work hours (08:00-18:00)
                    if 8 <= hour < 18:
                        data.append({
                            'timestamp': timestamp,
                            'kwh': kwh_per_interval,
                            'band': 'day'
                        })

        df = pd.DataFrame(data)
        logger.info(
            f"Generated remote work profile: {len(df)} intervals, "
            f"{df['kwh'].sum():.0f} kWh total"
        )
        return df

    def combine_profiles(self, base_df: pd.DataFrame, scenario_df: pd.DataFrame) -> pd.DataFrame:
        """
        Combine base consumption profile with scenario profile.

        Args:
            base_df: Original consumption profile
            scenario_df: Scenario consumption profile

        Returns:
            Combined DataFrame
        """
        combined = pd.concat([base_df, scenario_df], ignore_index=True)
        combined['timestamp'] = pd.to_datetime(combined['timestamp'])
        combined = combined.sort_values('timestamp').reset_index(drop=True)

        logger.info(
            f"Combined profiles: {len(combined)} intervals, "
            f"{combined['kwh'].sum():.0f} kWh total"
        )
        return combined

    def combine_multiple_scenarios(
        self,
        base_df: pd.DataFrame,
        start_month: str,
        end_month: str,
        base_consumption_kwh: float,
        scenarios: list  # List of {scenario_id, answers}
    ) -> pd.DataFrame:
        """
        Combine base consumption with multiple scenarios.

        Args:
            base_df: Original consumption profile
            start_month: Start month
            end_month: End month
            base_consumption_kwh: Base consumption
            scenarios: List of scenario dicts with scenario_id and answers

        Returns:
            Combined DataFrame with all scenarios applied
        """
        combined_df = base_df.copy()

        for scenario in scenarios:
            scenario_id = scenario['scenario_id']
            answers = scenario['answers']

            # Generate profile for this scenario
            if scenario_id == 'electric_vehicle':
                scenario_df = self.generate_electric_vehicle_profile(
                    start_month, end_month,
                    answers.get('annual_km', 12000),
                    answers.get('consumption_kwh_per_100km', 17),
                    answers.get('charging_hours', '20:00-08:00')
                )
            elif scenario_id == 'heat_pump':
                scenario_df = self.generate_heat_pump_profile(
                    start_month, end_month,
                    answers.get('annual_heating_kwh', 4000),
                    answers.get('heating_months', '10,11,12,1,2,3,4')
                )
            elif scenario_id == 'solar_panels':
                scenario_df = self.generate_solar_panels_profile(
                    start_month, end_month,
                    answers.get('annual_production_kwh', 3000),
                    answers.get('peak_hours', '08:00-16:00')
                )
            elif scenario_id == 'remote_work':
                scenario_df = self.generate_remote_work_profile(
                    start_month, end_month,
                    base_consumption_kwh,
                    answers.get('additional_consumption_percent', 15),
                    answers.get('working_days_per_week', 5)
                )
            else:
                continue

            # Combine with current combined_df
            combined_df = pd.concat([combined_df, scenario_df], ignore_index=True)

        # Sort and aggregate
        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)

        logger.info(
            f"Combined {len(scenarios)} scenarios: {len(combined_df)} intervals, "
            f"{combined_df['kwh'].sum():.0f} kWh total"
        )
        return combined_df
