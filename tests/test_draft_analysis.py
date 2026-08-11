#!/usr/bin/env python3
"""
Unit Test Suite for Draft Analytics & Math Invariants V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_draft_analysis.py
Verifies:
  1. 5 Mathematical Invariants
  2. Dynamic First-Pick and First-Ban Chronological Detection
  3. Hero Draft Uniqueness & Constraint Integrity
"""

import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.analytics.draft_analysis import verify_invariants
from scripts.validate_esports import audit_draft_sequence

class TestDraftAnalysis(unittest.TestCase):

    def setUp(self):
        matches_path = os.path.join(BASE_DIR, 'esports/matches/m5_knockout_matches.json')
        with open(matches_path, 'r', encoding='utf-8') as f:
            self.matches = json.load(f).get('data', [])

    def test_math_invariants(self):
        # Must pass without raising AssertionError
        verify_invariants(self.matches)

    def test_dynamic_first_pick_and_first_ban(self):
        for m in self.matches:
            draft = m.get('draft', [])
            first_ban = next((a for a in draft if a['type'] == 'ban'), None)
            first_pick = next((a for a in draft if a['type'] == 'pick'), None)

            self.assertIsNotNone(first_ban, f"Match {m['match_id']} missing first ban")
            self.assertIsNotNone(first_pick, f"Match {m['match_id']} missing first pick")

            self.assertEqual(first_ban['action'], 1, f"First ban in match {m['match_id']} must be action 1")
            self.assertEqual(first_pick['action'], 7, f"First pick in match {m['match_id']} must be action 7")

    def test_draft_completeness_and_hero_uniqueness(self):
        for m in self.matches:
            draft = m.get('draft', [])
            is_contiguous, state_valid = audit_draft_sequence(draft)

            self.assertTrue(is_contiguous, f"Draft action sequence in match {m['match_id']} must be contiguous 1..N")
            self.assertTrue(state_valid, f"Hero draft uniqueness violated in match {m['match_id']}")

            tot = len(draft)
            bans = sum(1 for a in draft if a['type'] == 'ban')
            picks = sum(1 for a in draft if a['type'] == 'pick')

            self.assertIn(tot, [19, 20], f"Total actions in match {m['match_id']} must be 19 or 20")
            self.assertEqual(picks, 10, f"Total picks in match {m['match_id']} must be 10")
            self.assertIn(bans, [9, 10], f"Total bans in match {m['match_id']} must be 9 or 10")

if __name__ == '__main__':
    unittest.main()
