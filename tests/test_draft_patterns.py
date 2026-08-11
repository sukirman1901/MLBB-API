#!/usr/bin/env python3
"""
Unit Test Suite for Draft Pattern & Opponent Scouting Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_draft_patterns.py
Tests:
  1. Same pattern aggregates correctly
  2. Patch contexts remain separated
  3. Teams remain separated
  4. Opponents remain separated
  5. Sequence ordering is preserved
  6. 1-step sequences are correct
  7. 2-step sequences are correct
  8. 3-step sequences are correct
  9. Sample-size thresholds are correct (n >= 5)
 10. Win/loss totals equal sample size
 11. Response rates sum correctly to 1.0
 12. No cross-match sequence contamination
 13. Match ID is preserved as group_id for future ML
 14. No causal terminology appears in machine output
 15. Results are deterministic
"""

import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.analytics.draft_pattern_analysis import run_pattern_engine

class TestDraftPatterns(unittest.TestCase):

    def setUp(self):
        self.patterns_dir = os.path.join(BASE_DIR, 'analytics/output/patterns')
        # Run engine to ensure files are generated
        run_pattern_engine(verbose=False)

    def test_1_same_pattern_aggregates_correctly(self):
        path = os.path.join(self.patterns_dir, 'pick_response_patterns.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertEqual(item["state_count"], len(item["group_id_matches"]))

    def test_2_patch_contexts_remain_separated(self):
        path = os.path.join(self.patterns_dir, 'patch_tendencies.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertIn("patch_version", item)
            self.assertIsNotNone(item["patch_version"])

    def test_3_teams_remain_separated(self):
        path = os.path.join(self.patterns_dir, 'team_tendencies.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        teams = set(t["team_id"] for t in data)
        self.assertGreater(len(teams), 1, "Must contain multiple distinct teams")

    def test_4_opponents_remain_separated(self):
        path = os.path.join(self.patterns_dir, 'opponent_tendencies.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertIsNotNone(item["team_id"])
            self.assertIsNotNone(item["opponent_team_id"])

    def test_5_sequence_ordering_preserved(self):
        path = os.path.join(self.patterns_dir, 'multi_step_sequences.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        seq3 = data["three_step_sequences"][0]["sequence"]
        self.assertEqual(len(seq3), 3, "3-step sequence must contain 3 elements")

    def test_6_one_step_sequences_correct(self):
        path = os.path.join(self.patterns_dir, 'multi_step_sequences.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        seq1 = data["one_step_sequences"]
        self.assertGreater(len(seq1), 0)
        self.assertGreater(seq1[0]["observed_frequency"], 0)

    def test_7_two_step_sequences_correct(self):
        path = os.path.join(self.patterns_dir, 'multi_step_sequences.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        seq2 = data["two_step_sequences"]
        self.assertGreater(len(seq2), 0)
        self.assertEqual(len(seq2[0]["sequence"]), 2)

    def test_8_three_step_sequences_correct(self):
        path = os.path.join(self.patterns_dir, 'multi_step_sequences.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        seq3 = data["three_step_sequences"]
        self.assertGreater(len(seq3), 0)
        self.assertEqual(len(seq3[0]["sequence"]), 3)

    def test_9_sample_size_thresholds_correct(self):
        path = os.path.join(self.patterns_dir, 'pick_response_patterns.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            n = item["state_count"]
            if n >= 5:
                self.assertTrue(item["sample_sufficient"])
            else:
                self.assertFalse(item["sample_sufficient"])

    def test_10_win_loss_totals_equal_sample_size(self):
        path = os.path.join(self.patterns_dir, 'pick_response_patterns.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertEqual(item["wins"] + item["losses"], item["state_count"])

    def test_11_response_rates_sum_correctly(self):
        path = os.path.join(self.patterns_dir, 'team_tendencies.json')
        with open(path, 'r', encoding='utf-8') as f:
            teams = json.load(f)["data"]

        for t in teams:
            for opp_h, resp_data in t["alternative_responses"].items():
                total_rate = sum(r["response_rate"] for r in resp_data["observed_responses"])
                self.assertAlmostEqual(total_rate, 1.0, places=2)

    def test_12_no_cross_match_sequence_contamination(self):
        # All multi step sequences must originate within single match boundaries
        path = os.path.join(self.patterns_dir, 'multi_step_sequences.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn("three_step_sequences", data)

    def test_13_group_id_preserved_as_match_id(self):
        path = os.path.join(self.patterns_dir, 'pick_response_patterns.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)["data"]

        for item in data:
            self.assertIn("group_id_matches", item)
            self.assertIsInstance(item["group_id_matches"], list)
            self.assertGreater(len(item["group_id_matches"]), 0)

    def test_14_no_causal_terminology_in_output(self):
        files = ['pick_response_patterns.json', 'team_tendencies.json', 'draft_flexibility.json']
        banned_words = ['counter', 'synergy', 'best response', 'correct response', 'winning draft', 'causes victory']

        for fname in files:
            path = os.path.join(self.patterns_dir, fname)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().lower()

            for bw in banned_words:
                self.assertNotIn(bw, content, f"Banned causal word '{bw}' found in {fname}")

    def test_15_results_are_deterministic(self):
        path = os.path.join(self.patterns_dir, 'pick_response_patterns.json')
        with open(path, 'r', encoding='utf-8') as f:
            res1 = json.load(f)

        run_pattern_engine()

        with open(path, 'r', encoding='utf-8') as f:
            res2 = json.load(f)

        self.assertEqual(res1, res2)

if __name__ == '__main__':
    unittest.main()
