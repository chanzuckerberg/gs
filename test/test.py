#!/usr/bin/env python
# coding: utf-8

import os, sys, unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import gs, tweak
from gs import cli

class TestGS(unittest.TestCase):
    def test_basic_gs_commands(self):
        config = tweak.Config("gs", save_on_exit=False)
        client = gs.GSClient(config=config)
        cli.ls.main([], standalone_mode=False)
        cli.ls.main(["--json"], standalone_mode=False)
