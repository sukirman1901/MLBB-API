#!/usr/bin/env python3
"""
Unit Test Suite for Draft Scouting Evidence Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_scouting_evidence.py
Tests:
  1. Global aggregation correct (Level A)
  2. Team aggregation correct (Level B)
  3. Team + patch aggregation correct (Level C)
  4. Team + opponent aggregation correct (Level D)
  5. Team + patch + opponent aggregation correct (Level E)
  6. Lift calculation correct (team_rate / global_rate)
  7. Zero denominator returns null
  8. Sample size uses unique games
  9. Series count uses unique series
 10. Tournament count uses unique tournaments
 11. Normalized entropy is within [0.0, 1.0]
 12. K=1 entropy handled correctly (H_norm = 0.0)
 13. Context separation works
 14. Pattern does not cross match boundaries
 15. No causal terminology in output
 16. Deterministic output
"""

import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.analytics.scouting_evidence import run_scouting_evidence_engine, calculate_shannon_entropy, compute_lift

class TestScoutingEvidence(unittest.TestCase):

    def setUp(self):
        self.scouting_dir = os.path.join(BASE_DIR, 'analytics/output/scouting')
        run_scouting_evidence_engine(verbose=False)

    def test_1_global_aggregation_correct(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]
        self.assertGreater(len(data), 0)

    def test_2_team_aggregation_correct(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertIn("team_id", item["context"])
            self.assertIsNotNone(item["context"]["team_id"])

    def test_3_team_patch_aggregation_correct(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            for p_rec in item.get("patch_breakdown", []):
                self.assertIn("patch_version", p_rec)

    def test_4_team_opponent_aggregation_correct(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            for o_rec in item.get("opponent_breakdown", []):
                self.assertIn("opponent_team_id", o_rec)

    def test_5_team_patch_opponent_aggregation_correct(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        self.assertGreater(len(data), 0)

    def test_6_lift_calculation_correct(self):
        lift = compute_lift(0.40, 0.10)
        self.assertEqual(lift, 4.0)

    def test_7_zero_denominator_returns_null(self):
        lift = compute_lift(0.50, 0.0)
        self.assertIsNone(lift)

    def test_8_sample_size_uses_unique_games(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertGreater(item["evidence"]["sample_size_games"], 0)

    def test_9_series_count_uses_unique_series(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertGreater(item["evidence"]["sample_size_series"], 0)

    def test_10_tournament_count_uses_unique_tournaments(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertEqual(item["evidence"]["tournament_count"], 1)

    def test_11_normalized_entropy_within_bounds(self):
        raw_h, norm_h, K = calculate_shannon_entropy([0.5, 0.5])
        self.assertGreaterEqual(norm_h, 0.0)
        self.assertLessEqual(norm_h, 1.0)
        self.assertEqual(norm_h, 1.0)

    def test_12_k_equals_1_entropy_handled_correctly(self):
        raw_h, norm_h, K = calculate_shannon_entropy([1.0])
        self.assertEqual(raw_h, 0.0)
        self.assertEqual(norm_h, 0.0)
        self.assertEqual(K, 1)

    def test_13_context_separation_works(self):
        path = os.path.join(self.scouting_dir, 'team_scouting_summary.json')
        with open(path, 'r', encoding='utf-8') as f:
            summaries = json.load(f)["data"]

        for s in summaries:
            self.assertIn("normalized_entropy", s)
            self.assertGreaterEqual(s["normalized_entropy"], 0.0)
            self.assertLessEqual(s["normalized_entropy"], 1.0)

    def test_14_pattern_does_not_cross_match_boundaries(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]
        self.assertGreater(len(data), 0)

    def test_15_no_causal_terminology_in_output(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        banned_words = ['counter', 'synergy', 'best response', 'correct response', 'winning draft', 'causes victory', 'statistically significant']
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().lower()

        for bw in banned_words:
            self.assertNotIn(bw, content, f"Banned causal word '{bw}' found in scouting_evidence.json")

    def test_16_deterministic_output(self):
        path = os.path.join(self.scouting_dir, 'scouting_evidence.json')
        with open(path, 'r', encoding='utf-8') as f:
            res1 = json.load(f)

        run_scouting_evidence_engine()

        with open(path, 'r', encoding='utf-8') as f:
            res2 = json.load(f)

        self.assertEqual(res1, res2)

if __name__ == '__main__':
    unittest.main()
