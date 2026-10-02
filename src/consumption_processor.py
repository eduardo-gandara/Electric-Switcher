"""
Consumption Processor - Analysis of ESB Networks consumption
Cleans CSV, constructs profile of 30 minutes per band, month and hour.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict


class ConsumptionProcessor:
    """Processes ESB Networks consumption data."""

    NIGHT_START = 21  # 21:00
    NIGHT_END = 8    # 08:00
    PEAK_START = 17  # 17:00
    PEAK_END = 19    # 19:00
    PEAK_WEEKDAYS_ONLY = True  # Only Monday-Friday

    def __init__(self, csv_path: str):
        """Load CSV from ESB Networks."""
        self.raw_df = pd.read_csv(csv_path)
        self.df = None
        self.quality_report = {}

    def _get_band(self, timestamp: pd.Timestamp) -> str:
        """Determine band (day, night, peak) based on timestamp."""
        hour = timestamp.hour
        weekday = timestamp.weekday()  # 0=Monday, 6=Sunday

        # Peak band: 17:00-19:00 only Monday-Friday
        if self.PEAK_WEEKDAYS_ONLY:
            if hour >= self.PEAK_START and hour < self.PEAK_END and weekday < 5:
                return 'peak'
        else:
            if hour >= self.PEAK_START and hour < self.PEAK_END:
                return 'peak'

        # Night band: 21:00-08:00
        if hour >= self.NIGHT_START or hour < self.NIGHT_END:
            return 'night'

        # Day band: rest
        return 'day'

    def _normalize_column_name(self, col: str) -> str:
        """Normalize column name for matching."""
        return col.lower().strip()

    def clean(self) -> 'ConsumptionProcessor':
        """
        Clean CSV: remove duplicates, impute gaps, adjust DST changes.
        """
        df = self.raw_df.copy()

        # Detect and rename columns with smart matching
        column_mapping = self._detect_columns(df)

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # Check if we have the required columns
        required_cols = ['meter_id', 'kwh', 'read_type', 'timestamp']
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            print(f"Warning: Missing columns after rename: {missing}")
            print(f"Available columns: {df.columns.tolist()}")

        # Initial validation
        initial_rows = len(df)

        # Remove exact duplicates
        duplicates = df.duplicated(subset=['meter_id', 'timestamp', 'kwh']).sum()
        df = df.drop_duplicates(subset=['meter_id', 'timestamp', 'kwh'])

        # Parse timestamp (format dd-mm-yyyy hh:mm, descending order)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%d-%m-%Y %H:%M', errors='coerce')

        # Sort by timestamp
        df = df.sort_values('timestamp')

        # Confirm that Read Value is numeric (kWh)
        if 'kwh' in df.columns:
            df['kwh'] = pd.to_numeric(df['kwh'], errors='coerce')

        # Mark estimated readings
        if 'read_type' in df.columns:
            df['is_estimated'] = df['read_type'].str.lower().str.contains('estimated', na=False)

        # Impute gaps: ~80 missing intervals
        if 'timestamp' in df.columns and 'kwh' in df.columns:
            df = df.dropna(subset=['timestamp', 'kwh'])

            # Create expected timestamp (every 30 min)
            min_time = df['timestamp'].min()
            max_time = df['timestamp'].max()

            if pd.notna(min_time) and pd.notna(max_time):
                expected_times = pd.date_range(min_time, max_time, freq='30min')

                # Find missing times
                actual_times = set(df['timestamp'])
                missing_times = [t for t in expected_times if t not in actual_times]

                # Impute missing intervals
                for missing_time in missing_times:
                    nearby = df[(df['timestamp'] >= missing_time - timedelta(hours=2)) &
                               (df['timestamp'] <= missing_time + timedelta(hours=2))]
                    if len(nearby) > 0:
                        imputed_value = nearby['kwh'].median()
                    else:
                        imputed_value = df['kwh'].median()

                    new_row = pd.DataFrame({
                        'meter_id': [df['meter_id'].iloc[0]] if 'meter_id' in df.columns else [None],
                        'timestamp': [missing_time],
                        'kwh': [imputed_value],
                        'read_type': ['estimated'],
                        'is_estimated': [True]
                    })
                    df = pd.concat([df, new_row], ignore_index=True)

                df = df.sort_values('timestamp')

        # Record quality
        self.quality_report = {
            'initial_rows': initial_rows,
            'duplicates_removed': duplicates,
            'final_rows': len(df),
            'missing_intervals_imputed': len(missing_times) if 'missing_times' in locals() else 0,
            'date_range': f"{df['timestamp'].min() if 'timestamp' in df.columns else 'N/A'} to {df['timestamp'].max() if 'timestamp' in df.columns else 'N/A'}",
            'estimated_readings': df['is_estimated'].sum() if 'is_estimated' in df.columns else 0
        }

        self.df = df
        return self

    def _detect_columns(self, df: pd.DataFrame) -> dict:
        """
        Detect column names with flexible matching.
        Returns mapping dict {original_name: new_name}.
        """
        mapping = {}
        col_list = df.columns.tolist()

        meter_col = None
        kwh_col = None
        type_col = None
        timestamp_col = None

        # Search for columns by partial match
        for col in col_list:
            col_lower = self._normalize_column_name(col)

            # Look for meter ID column
            if not meter_col:
                if any(x in col_lower for x in ['mprn', 'meter serial', 'meter id']):
                    meter_col = col
                    continue

            # Look for consumption column
            if not kwh_col:
                if any(x in col_lower for x in ['read value', 'kwh', 'consumption', 'kw/h']):
                    kwh_col = col
                    continue

            # Look for read type column
            if not type_col:
                if 'read type' in col_lower or col_lower == 'type':
                    type_col = col
                    continue

            # Look for timestamp column
            if not timestamp_col:
                if 'read date' in col_lower or ('date' in col_lower and 'time' in col_lower):
                    timestamp_col = col
                    continue

        # Build mapping
        if meter_col:
            mapping[meter_col] = 'meter_id'
        if kwh_col:
            mapping[kwh_col] = 'kwh'
        if type_col:
            mapping[type_col] = 'read_type'
        if timestamp_col:
            mapping[timestamp_col] = 'timestamp'

        # Fallback: exact matches
        if not meter_col:
            for col in col_list:
                if col == 'MPRN, Meter Serial Number':
                    mapping[col] = 'meter_id'

        if not kwh_col:
            for col in col_list:
                if col == 'Read Value':
                    mapping[col] = 'kwh'

        if not type_col:
            for col in col_list:
                if col == 'Read Type':
                    mapping[col] = 'read_type'

        if not timestamp_col:
            for col in col_list:
                if col == 'Read Date and End Time':
                    mapping[col] = 'timestamp'

        return mapping

    def build_profile(self) -> pd.DataFrame:
        """
        Build profile of 30 minutes per band, month and hour.
        Returns DataFrame with [timestamp, kwh, band].
        """
        if self.df is None:
            raise ValueError("Run clean() first")

        df = self.df.copy()
        df = df.dropna(subset=['timestamp', 'kwh'])

        # Add band
        df['band'] = df['timestamp'].apply(self._get_band)

        # Validate: kWh must be positive
        invalid_kwh = (df['kwh'] < 0).sum()
        if invalid_kwh > 0:
            print(f"Warning: {invalid_kwh} negative readings removed")
            df = df[df['kwh'] >= 0]

        # Convert to native Python types (avoid numpy int64 serialization issues)
        result = df[['timestamp', 'kwh', 'band']].copy()
        result['kwh'] = result['kwh'].astype(float)
        result = result.reset_index(drop=True)

        return result

    def get_quality_report(self) -> Dict:
        """Get data quality report."""
        return self.quality_report

    def validate(self) -> Tuple[bool, str]:
        """
        Validate that data meets minimum criteria.
        Returns (valid, message).
        """
        if self.df is None:
            return False, "CSV not processed"

        messages = []

        # Check date range
        min_date = self.df['timestamp'].min() if 'timestamp' in self.df.columns else None
        max_date = self.df['timestamp'].max() if 'timestamp' in self.df.columns else None

        if pd.isna(min_date) or pd.isna(max_date):
            return False, "Invalid timestamp data"

        expected_min = pd.to_datetime('2024-10-01')
        expected_max = pd.to_datetime('2026-09-30')

        if min_date > expected_min:
            messages.append(f"Start date {min_date.date()} after expected {expected_min.date()}")
        if max_date < expected_max:
            messages.append(f"End date {max_date.date()} before expected {expected_max.date()}")

        # Check coverage
        total_intervals = (max_date - min_date) / timedelta(minutes=30)
        actual_intervals = len(self.df)
        coverage = actual_intervals / total_intervals if total_intervals > 0 else 0

        if coverage < 0.90:
            messages.append(f"Low coverage: {coverage:.1%}")

        # Check consumption
        if 'kwh' in self.df.columns:
            total_kwh = self.df['kwh'].sum()
            expected_kwh = 4_000

            if total_kwh < expected_kwh * 0.5 or total_kwh > expected_kwh * 2:
                messages.append(f"Unusual consumption: {total_kwh:.0f} kWh")

        valid = len(messages) == 0
        return valid, "; ".join(messages) if messages else "✓ Data valid"


if __name__ == '__main__':
    print("Consumption Processor loaded")
