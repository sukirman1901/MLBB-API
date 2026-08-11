#!/usr/bin/env python3
"""
Unit Test Suite for Patch Context & Temporal Semantics V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_patch_context.py
Tests:
  1. Explicit match patch takes precedence (Level 1)
  2. Verified tournament PatchWindow resolves correctly (Level 2)
  3. Date inference is marked LOW confidence (Level 3)
  4. Unresolved patch remains None / UNKNOWN (Level 4)
  5. BEFORE_RELEASE temporal relationship correctly identified for advance tournament server builds
  6. days_since_competitive_effective >= 0 when effective_from predates match
  7. Boundary dates are handled correctly (inclusive)
  8. Overlapping PatchWindows are detected and flagged
  9. Match from another tournament cannot inherit wrong PatchWindow
 10. Same input produces deterministic assignment
"""

import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.ingestion.assign_patch_context import assign_patch_context_to_match, check_overlapping_windows, parse_iso8601

class TestPatchContextAssignment(unittest.TestCase):

    def setUp(self):
        self.patches = [
            {
                "patch_id": "patch-1.8.44",
                "version": "1.8.44",
                "release_date": "2023-12-20T00:00:00Z",
                "source_url": "https://liquipedia.net/mobilelegends/Patch_1.8.44"
            }
        ]
        self.windows = [
            {
                "patch_window_id": "pw-m5-ko-1.8.44",
                "tournament_id": "m5-world-championship",
                "stage": "Knockout Stage",
                "patch_version": "1.8.44",
                "effective_from": "2023-12-09T00:00:00Z",
                "effective_until": "2023-12-17T23:59:59Z",
                "status": "VERIFIED"
            }
        ]

    def test_1_explicit_match_patch_precedence(self):
        match = {
            "date": "2023-12-09T14:00:00Z",
            "tournament_id": "m5-world-championship",
            "stage": "Knockout Stage",
            "patch": "1.8.44",
            "patch_source": "explicit"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["assignment_method"], "explicit_match_source")
        self.assertEqual(res["assignment_confidence"], "HIGH")
        self.assertEqual(res["version"], "1.8.44")

    def test_2_verified_tournament_window_resolution(self):
        match = {
            "date": "2023-12-09T14:00:00Z",
            "tournament_id": "m5-world-championship",
            "stage": "Knockout Stage"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["assignment_method"], "verified_tournament_window")
        self.assertEqual(res["assignment_confidence"], "HIGH")
        self.assertEqual(res["version"], "1.8.44")

    def test_3_date_inference_low_confidence(self):
        match = {
            "date": "2023-12-25T14:00:00Z",
            "tournament_id": "other-tournament",
            "stage": "Group Stage"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["assignment_method"], "date_inference")
        self.assertEqual(res["assignment_confidence"], "LOW")

    def test_4_unresolved_patch_remains_null(self):
        match = {
            "date": "2020-01-01T00:00:00Z",
            "tournament_id": "ancient-tournament",
            "stage": "Group Stage"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["assignment_method"], "unresolved")
        self.assertEqual(res["assignment_confidence"], "UNKNOWN")
        self.assertIsNone(res["version"])

    def test_5_before_release_temporal_relationship(self):
        match = {
            "date": "2023-12-09T14:00:00Z",
            "tournament_id": "m5-world-championship",
            "stage": "Knockout Stage"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["temporal_relationship"], "BEFORE_RELEASE")
        self.assertEqual(res["days_since_patch_release"], -11)
        self.assertEqual(res["days_before_patch_release"], 11)

    def test_6_days_since_competitive_effective_math(self):
        match = {
            "date": "2023-12-09T14:00:00Z",
            "tournament_id": "m5-world-championship",
            "stage": "Knockout Stage"
        }
        res = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res["days_since_competitive_effective"], 0)
        self.assertGreaterEqual(res["days_since_competitive_effective"], 0)

    def test_7_boundary_dates_inclusive(self):
        match_start = {"date": "2023-12-09T00:00:00Z", "tournament_id": "m5-world-championship", "stage": "Knockout Stage"}
        match_end = {"date": "2023-12-17T23:59:59Z", "tournament_id": "m5-world-championship", "stage": "Knockout Stage"}

        res_start = assign_patch_context_to_match(match_start, self.patches, self.windows)
        res_end = assign_patch_context_to_match(match_end, self.patches, self.windows)

        self.assertEqual(res_start["assignment_method"], "verified_tournament_window")
        self.assertEqual(res_end["assignment_method"], "verified_tournament_window")

    def test_8_overlapping_patch_windows_detected(self):
        bad_windows = [
            {"patch_window_id": "w1", "tournament_id": "t1", "stage": "s1", "effective_from": "2023-12-01T00:00:00Z", "effective_until": "2023-12-10T23:59:59Z"},
            {"patch_window_id": "w2", "tournament_id": "t1", "stage": "s1", "effective_from": "2023-12-08T00:00:00Z", "effective_until": "2023-12-15T23:59:59Z"}
        ]
        with self.assertRaises(ValueError):
            check_overlapping_windows(bad_windows)

    def test_9_cross_tournament_isolation(self):
        match_other = {"date": "2023-12-09T14:00:00Z", "tournament_id": "mpl-ph-s12", "stage": "Playoffs"}
        res = assign_patch_context_to_match(match_other, self.patches, self.windows)
        self.assertNotEqual(res["patch_window_id"], "pw-m5-ko-1.8.44")

    def test_10_deterministic_assignment(self):
        match = {"date": "2023-12-09T14:00:00Z", "tournament_id": "m5-world-championship", "stage": "Knockout Stage"}
        res1 = assign_patch_context_to_match(match, self.patches, self.windows)
        res2 = assign_patch_context_to_match(match, self.patches, self.windows)
        self.assertEqual(res1, res2)

if __name__ == '__main__':
    unittest.main()
