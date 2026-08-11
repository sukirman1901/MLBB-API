#!/usr/bin/env python3
"""
Unit Test Suite for Meta Tracing Engine V1
Author: sukirman1901
Repository: https://github.com/sukirman1901/MLBB-API

Location: tests/test_meta_tracing.py
Asserts patch metadata integrity, emergence delta calculations, and JSON export validation.
"""

import json
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestMetaTracing(unittest.TestCase):

    def test_patch_catalog_exists(self):
        patch_path = os.path.join(BASE_DIR, 'patches/patches.json')
        self.assertTrue(os.path.exists(patch_path), "patches/patches.json must exist")
        with open(patch_path, 'r', encoding='utf-8') as f:
            data = json.load(f)['data']
        self.assertGreaterEqual(len(data), 1, "Must contain at least 1 patch record")

    def test_changelog_structure(self):
        cl_path = os.path.join(BASE_DIR, 'patches/changelogs/patch_1_8_44.json')
        self.assertTrue(os.path.exists(cl_path), "patch_1_8_44.json must exist")
        with open(cl_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data.get('patch_id'), 'patch-1.8.44')
        self.assertIn('hero_adjustments', data)

    def test_emerging_signals_export(self):
        es_path = os.path.join(BASE_DIR, 'analytics/output/meta/emerging_signals.json')
        if os.path.exists(es_path):
            with open(es_path, 'r', encoding='utf-8') as f:
                data = json.load(f)['data']
            for signal in data:
                self.assertIn('signal_type', signal)
                self.assertIn('delta', signal)
                self.assertGreaterEqual(signal['delta'], 0.15)
                self.assertIn('sample_sufficient', signal)

if __name__ == '__main__':
    unittest.main()
