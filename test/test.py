#!/usr/bin/env python
# coding: utf-8

import os, sys, unittest, uuid, tempfile, time, logging

try:
    from tempfile import TemporaryDirectory
except ImportError:
    from gs.packages.backports.tempfile import TemporaryDirectory

import gs, tweak
from gs import cli

from gs.util.compat import USING_PYTHON2

logging.basicConfig(level=logging.DEBUG)

class TestGS(unittest.TestCase):
    test_bucket = os.environ["GS_TEST_BUCKET"]
    test_id = int(time.time() * 1000)

    def test_ls_commands(self):
        config = tweak.Config("gs", save_on_exit=False)
        client = gs.GSClient(config=config)
        cli.ls.main([], standalone_mode=False)
        cli.ls.main(["--json"], standalone_mode=False)

    def test_rw_commands(self):
        with tempfile.NamedTemporaryFile() as tf1, tempfile.NamedTemporaryFile() as tf2:
            payload = os.urandom(1024 * 1024 + 1)
            tf1.write(payload)
            tf1.flush()
            tf2.write(payload[:16])
            tf2.flush()
            test_prefix = "gs://{}/{}".format(self.test_bucket, self.test_id)
            furl1 = os.path.join(test_prefix, os.path.basename(tf1.name))
            furl2 = os.path.join(test_prefix, os.path.basename(tf2.name))
            cli.cp.main([tf1.name, tf2.name, test_prefix], standalone_mode=False)
            cli.ls.main([test_prefix], standalone_mode=False)
            # cli.presign.main([furl1], standalone_mode=False)
            with TemporaryDirectory() as td:
                cli.cp.main([furl1, furl2, td], standalone_mode=False)
                with open(os.path.join(td, tf1.name), "rb") as fh:
                    self.assertEqual(fh.read(), payload)
                with open(os.path.join(td, tf2.name), "rb") as fh:
                    self.assertEqual(fh.read(), payload[:16])
                cli.cp.main([furl1, furl1 + ".2"], standalone_mode=False)
                cli.mv.main([furl1, furl1 + ".3"], standalone_mode=False)
                cli.cp.main([furl1 + ".3", furl1 + ".4"], standalone_mode=False)
                cli.rm.main([furl1 + ".2", furl1 + ".3"], standalone_mode=False)
                cli.sync.main([test_prefix, td], standalone_mode=False)
                cli.sync.main([td, test_prefix], standalone_mode=False)
                cli.rm.main([test_prefix, "--recursive"], standalone_mode=False)

if __name__ == "__main__":
    unittest.main()
