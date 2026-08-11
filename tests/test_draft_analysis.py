#!/usr/bin/env python3
"""
Unit Test Suite for Draft Analytics Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_draft_analysis.py
Asserts math invariants, sample size awareness, sample_sufficient presence, and export integrity.
"""

import json
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestDraftAnalytics(unittest.TestCase):

    def setUp(self):
        matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
        with open(matches_path, 'r', encoding='utf-8') as f:
            self.matches = json.load(f)['data']

    def test_side_win_invariant(self):
        total_games = len(self.matches)
        blue_wins = sum(1 for m in self.matches if m['winner_team_id'] == m['blue_side'])
        red_wins = sum(1 for m in self.matches if m['winner_team_id'] == m['red_side'])
        self.assertEqual(blue_wins + red_wins, total_games, "Blue wins + Red wins must equal total games")

    def test_pick_ban_sum_invariant(self):
        for m in self.matches:
            draft = m.get('draft', [])
            picks = [a for a in draft if a['type'] == 'pick']
            bans = [a for a in draft if a['type'] == 'ban']
            self.assertLessEqual(len(picks), 10, f"Match {m['match_id']} has > 10 picks")
            self.assertLessEqual(len(bans), 10, f"Match {m['match_id']} has > 10 bans")

    def test_sample_sufficient_keys(self):
        hp_path = os.path.join(BASE_DIR, 'analytics/output/hero_priority.json')
        if os.path.exists(hp_path):
            with open(hp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)['data']
            for rec in data:
                st = rec['observed_stats']
                self.assertIn('sample_size', st)
                self.assertIn('sample_sufficient', st)
                self.assertEqual(st['sample_sufficient'], st['sample_size'] >= 5)

if __name__ == '__main__':
    unittest.main()
