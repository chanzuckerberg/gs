#!/usr/bin/env python
# coding: utf-8

import os, sys, unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import gs

class TestGS(unittest.TestCase):
    def test_basic_aegea_commands(self):
        pass
