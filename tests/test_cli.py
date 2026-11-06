from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentics_tools.cli import main
import test_installer


class CliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_installer.InstallerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def call(self, *arguments):
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=False), mock.patch("agentics_tools.cli.default_catalog", return_value=self.fixture.catalog), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(arguments))
        return code, output.getvalue(), error.getvalue()

    def test_list_outputs_machine_readable_catalog(self):
        code, output, _ = self.call("list", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output))

    def test_install_requires_selection(self):
        with self.assertRaises(SystemExit) as failure, contextlib.redirect_stderr(io.StringIO()):
            self.call("install", "--home", str(self.fixture.layout.home))
        self.assertEqual(failure.exception.code, 2)

    def test_cli_dry_run_does_not_create_home(self):
        home = self.fixture.layout.home / "unused"
        code, _, error = self.call("install", "--all", "--dry-run", "--home", str(home), "--codex-home", str(home / ".codex"))
        self.assertEqual(code, 0, error)
        self.assertFalse(home.exists())

    def test_all_update_does_not_hide_colliding_owned_role(self):
        from agentics_tools.installer import install
        install(self.fixture.catalog, self.fixture.layout, self.fixture.catalog.select(all_items=True))
        agent_item = next(item for item in self.fixture.catalog.items.values() if item["kind"] == "agent")
        source = self.fixture.catalog.root / agent_item["path"]
        (self.fixture.layout.agent_root / "collision.toml").write_bytes(source.read_bytes())
        code, _, error = self.call("update", "--all", "--home", str(self.fixture.layout.home), "--codex-home", str(self.fixture.layout.codex_home))
        self.assertEqual(code, 1)
        self.assertIn("collision", error)


if __name__ == "__main__":
    unittest.main()
