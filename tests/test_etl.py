"""
Unit Test Suite for ETL Pipeline
Tests data extraction, transformation rules, schema conformance, and edge case handling.
"""

import os
import sys
import unittest
import pandas as pd

# Add src to python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from etl_script import transform_data, get_config


class TestETLPipeline(unittest.TestCase):
    """Test cases for ETL transformation and configuration logic."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.sample_raw_df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5, 5],  # includes duplicate
            "value": [100.0, 200.0, 500.0, -10.0, float("nan"), 100.0],
        })

    def test_default_config_loader(self):
        """Test that default configuration falls back to LocalStack parameters."""
        config = get_config()
        self.assertIn("endpoint_url", config)
        self.assertIn("bucket_name", config)
        self.assertIn("raw_key", config)
        self.assertIn("processed_key", config)

    def test_transformation_cleans_and_deduplicates(self):
        """Test that transformation removes duplicates and invalid/negative numbers."""
        transformed = transform_data(self.sample_raw_df)

        # Duplicate row (5, 100.0) should be dropped
        # Negative value (-10.0) should be dropped
        # NaN value should be dropped
        self.assertEqual(len(transformed), 3)

    def test_computed_columns_and_tiers(self):
        """Test calculation of surcharge, total amount, and tier assignments."""
        test_df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [100.0, 200.0, 600.0]
        })
        transformed = transform_data(test_df)

        # Validate surcharge calculation (10%)
        self.assertEqual(transformed.loc[transformed["id"] == 1, "surcharge_amount"].values[0], 10.0)
        self.assertEqual(transformed.loc[transformed["id"] == 2, "surcharge_amount"].values[0], 20.0)
        self.assertEqual(transformed.loc[transformed["id"] == 3, "surcharge_amount"].values[0], 60.0)

        # Validate total amount calculation
        self.assertEqual(transformed.loc[transformed["id"] == 1, "total_amount"].values[0], 110.0)
        self.assertEqual(transformed.loc[transformed["id"] == 3, "total_amount"].values[0], 660.0)

        # Validate tier classification
        self.assertEqual(transformed.loc[transformed["id"] == 1, "tier"].values[0], "STANDARD")
        self.assertEqual(transformed.loc[transformed["id"] == 2, "tier"].values[0], "MEDIUM")
        self.assertEqual(transformed.loc[transformed["id"] == 3, "tier"].values[0], "HIGH")

    def test_metadata_injection(self):
        """Test that pipeline status and timestamp are attached to output."""
        test_df = pd.DataFrame({"id": [1], "value": [50.0]})
        transformed = transform_data(test_df)

        self.assertIn("pipeline_status", transformed.columns)
        self.assertEqual(transformed["pipeline_status"].values[0], "PROCESSED")
        self.assertIn("processed_at_utc", transformed.columns)


if __name__ == "__main__":
    unittest.main()
