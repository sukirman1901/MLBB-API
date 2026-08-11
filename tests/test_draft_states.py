#!/usr/bin/env python3
"""
Unit Test Suite for Draft State Dataset & Transition Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_draft_states.py
Tests:
  1. State 0 (before action 1) is empty for picks
  2. State N contains all actions 1..N
  3. State transitions are contiguous 1..N
  4. state_after equals applying action to state_before
  5. No duplicate heroes (pick/ban state constraints)
  6. Available heroes list is correct (all_canonical - picked - banned)
  7. First pick flag is dynamic
  8. First ban flag is dynamic
  9. Team-relative representation is correct
 10. 19-action M5 draft (match-m5-ko-14-g3) is handled correctly
 11. Final state equals original match draft
 12. Draft state IDs are deterministic ({match_id}-state-{action_number})
"""

import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.ingestion.build_draft_states import build_states_for_match, load_data

class TestDraftStates(unittest.TestCase):

    def setUp(self):
        self.all_canonical_hero_ids, self.matches = load_data()

    def test_1_state_0_empty_before_first_action(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        s1 = states[0]
        self.assertEqual(len(s1["state_before"]["blue"]["picks"]), 0)
        self.assertEqual(len(s1["state_before"]["red"]["picks"]), 0)

    def test_2_state_n_contains_all_actions_1_to_n(self):
        m = self.matches[0]
        states, count = build_states_for_match(m, self.all_canonical_hero_ids)
        final_state = states[-1]
        tot_picks = len(final_state["state_after"]["blue"]["picks"]) + len(final_state["state_after"]["red"]["picks"])
        tot_bans = len(final_state["state_after"]["blue"]["bans"]) + len(final_state["state_after"]["red"]["bans"])
        self.assertEqual(tot_picks + tot_bans, count)

    def test_3_state_transitions_contiguous(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        action_nums = [s["action_number"] for s in states]
        self.assertEqual(action_nums, list(range(1, len(states) + 1)))

    def test_4_state_after_equals_applying_action(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        for s in states:
            side = s["acting_side"]
            atype = s["action"]["type"]
            hid = s["action"]["hero_id"]
            before_list = s["state_before"][side]["picks" if atype == "pick" else "bans"]
            after_list = s["state_after"][side]["picks" if atype == "pick" else "bans"]
            self.assertEqual(after_list, before_list + [hid])

    def test_5_no_duplicate_heroes(self):
        for m in self.matches:
            states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
            for s in states:
                blue_p = set(s["state_after"]["blue"]["picks"])
                blue_b = set(s["state_after"]["blue"]["bans"])
                red_p = set(s["state_after"]["red"]["picks"])
                red_b = set(s["state_after"]["red"]["bans"])

                self.assertEqual(len(blue_p.intersection(red_p)), 0, f"Hero picked on both sides in {s['state_id']}")
                self.assertEqual(len(blue_b.intersection(red_b)), 0, f"Hero banned on both sides in {s['state_id']}")

    def test_6_available_heroes_correct(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        s1 = states[0]
        # State 1 before action 1 has 0 picks and 0 bans, so all canonical heroes must be available
        self.assertEqual(s1["available_heroes"], self.all_canonical_hero_ids)

    def test_7_first_pick_dynamic(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        fp_state = next(s for s in states if s["is_first_pick"])
        self.assertEqual(fp_state["action_number"], 7)
        self.assertEqual(fp_state["action_type"], "pick")

    def test_8_first_ban_dynamic(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        fb_state = next(s for s in states if s["is_first_ban"])
        self.assertEqual(fb_state["action_number"], 1)
        self.assertEqual(fb_state["action_type"], "ban")

    def test_9_team_relative_representation(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        for s in states:
            side = s["acting_side"]
            opp_side = "red" if side == "blue" else "blue"
            self.assertEqual(s["team_relative_before"]["acting_team"], s["state_before"][side])
            self.assertEqual(s["team_relative_before"]["opponent_team"], s["state_before"][opp_side])

    def test_10_nineteen_action_m5_draft_handled(self):
        m_19 = next(m for m in self.matches if m["match_id"] == "match-m5-ko-14-g3")
        states, count = build_states_for_match(m_19, self.all_canonical_hero_ids)
        self.assertEqual(count, 19)
        self.assertEqual(len(states), 19)
        self.assertEqual(states[-1]["state_id"], "match-m5-ko-14-g3-state-19")

    def test_11_final_state_equals_original_match_draft(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        final_state = states[-1]

        orig_blue_picks = [a["hero_id"] for a in m["draft"] if a["type"] == "pick" and a["team_id"] == m["blue_side"]]
        self.assertEqual(final_state["state_after"]["blue"]["picks"], orig_blue_picks)

    def test_12_draft_state_ids_deterministic(self):
        m = self.matches[0]
        states, _ = build_states_for_match(m, self.all_canonical_hero_ids)
        for s in states:
            self.assertEqual(s["state_id"], f"{m['match_id']}-state-{s['action_number']}")

if __name__ == '__main__':
    unittest.main()
