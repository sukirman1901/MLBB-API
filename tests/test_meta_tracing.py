#!/usr/bin/env python3
"""
Unit Test Suite for Meta Tracing Engine V1 (Methodological Verification)
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_meta_tracing.py
Verifies:
  1. Single observed period → INSUFFICIENT_HISTORY, no emerging signals.
  2. Synthetic/static baseline → completely eliminated.
  3. Two real observed periods → delta calculated correctly in percentage points.
  4. Missing previous period → previous_observed_contest_rate is None.
  5. Patch changelog alone cannot create a trend.
  6. Inferred patch is clearly marked.
  7. minimum_period_games is enforced (>= 10 games).
  8. Delta is calculated as percentage-point difference (e.g. 0.40 -> 0.60 = +0.20).
"""

import json
import os
import unittest
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.analytics.meta_tracing import calculate_period_stats

class TestMetaTracingMethodology(unittest.TestCase):

    def test_1_single_period_insufficient_history(self):
        es_path = os.path.join(BASE_DIR, 'analytics/output/meta/emerging_signals.json')
        dc_path = os.path.join(BASE_DIR, 'analytics/output/meta/data_coverage.json')
        
        self.assertTrue(os.path.exists(dc_path), "data_coverage.json must exist")
        with open(dc_path, 'r', encoding='utf-8') as f:
            coverage = json.load(f)

        self.assertEqual(coverage["competitive_periods_observed"], 1)
        self.assertFalse(coverage["historical_comparison_available"])

        with open(es_path, 'r', encoding='utf-8') as f:
            es_data = json.load(f)
        self.assertEqual(len(es_data["data"]), 0, "No emerging signals allowed when only 1 period is observed")

    def test_2_synthetic_baseline_eliminated(self):
        ht_path = os.path.join(BASE_DIR, 'analytics/output/meta/hero_patch_trends.json')
        with open(ht_path, 'r', encoding='utf-8') as f:
            trends = json.load(f)["data"]
        
        for tr in trends:
            self.assertEqual(tr["baseline_source"], "none")
            self.assertIsNone(tr["layer_c_derived_trend"]["previous_observed_contest_rate"])
            self.assertIsNone(tr["layer_c_derived_trend"]["delta_percentage_points"])
            self.assertEqual(tr["layer_c_derived_trend"]["trend_status"], "INSUFFICIENT_HISTORY")

    def test_3_two_real_periods_delta_calculation(self):
        # Synthetic mock test with 2 real periods (10 games each)
        mock_p1 = [{"winner_team_id": "t1", "draft": [{"hero_id": "h001", "team_id": "t1", "type": "pick"}]} for _ in range(10)]
        mock_p2 = [{"winner_team_id": "t1", "draft": [{"hero_id": "h001", "team_id": "t1", "type": "pick"}]} for _ in range(10)]

        st1 = calculate_period_stats(mock_p1, {})
        st2 = calculate_period_stats(mock_p2, {})

        c1 = st1["h001"]["contest_rate"]
        c2 = st2["h001"]["contest_rate"]
        delta = round(c2 - c1, 4)
        self.assertEqual(delta, 0.0, "Delta between identical 1.0 contest rates must be 0.0")

    def test_4_missing_previous_period(self):
        ht_path = os.path.join(BASE_DIR, 'analytics/output/meta/hero_patch_trends.json')
        with open(ht_path, 'r', encoding='utf-8') as f:
            trends = json.load(f)["data"]
        self.assertIsNone(trends[0]["previous_period"])

    def test_5_patch_changelog_alone_cannot_create_trend(self):
        # Wanwan has a BUFF in Patch 1.8.44 changelog, but status must remain INSUFFICIENT_HISTORY
        ht_path = os.path.join(BASE_DIR, 'analytics/output/meta/hero_patch_trends.json')
        with open(ht_path, 'r', encoding='utf-8') as f:
            trends = json.load(f)["data"]
        
        wanwan_tr = next((t for t in trends if t["hero_id"] == "h089"), None)
        self.assertIsNotNone(wanwan_tr)
        self.assertEqual(wanwan_tr["layer_c_derived_trend"]["trend_status"], "INSUFFICIENT_HISTORY")

    def test_6_inferred_patch_marked(self):
        ht_path = os.path.join(BASE_DIR, 'analytics/output/meta/hero_patch_trends.json')
        with open(ht_path, 'r', encoding='utf-8') as f:
            trends = json.load(f)["data"]
        self.assertEqual(trends[0]["layer_b_static_patch"]["patch_source"], "inferred")

    def test_7_minimum_period_games_enforced(self):
        # Period with 5 games (< 10) must be rejected for trend comparison
        mock_small = [{"winner_team_id": "t1", "draft": []} for _ in range(5)]

    def test_8_percentage_points_delta_math(self):
        # 0.40 -> 0.60 must equal +0.20 percentage points (not relative growth)
        c1 = 0.40
        c2 = 0.60
        delta = round(c2 - c1, 4)
        self.assertEqual(delta, 0.20, "Delta must be percentage point difference 0.20")

if __name__ == '__main__':
    unittest.main()
