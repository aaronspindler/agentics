"""Catalog checks use a small synthetic collection, independent of shipped prompts."""

import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentics_tools.catalog import Catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentics catalog ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.items = [
            {
                "id": "skill:change-plan",
                "kind": "skill",
                "name": "change-plan",
                "path": "skills/change-plan",
                "group": "core",
                "dependencies": ["agent:reviewer"],
                "resources": {"references/checklist.md": "references/checklist.md"},
            },
            {
                "id": "skill:runtime-probe",
                "kind": "skill",
                "name": "runtime-probe",
                "path": "skills/runtime-probe",
                "group": "ops",
                "dependencies": [],
                "resources": {},
            },
            {
                "id": "agent:reviewer",
                "kind": "agent",
                "name": "reviewer",
                "path": "agents/reviewer.toml",
                "group": "github",
                "dependencies": [],
                "resources": {},
            },
        ]
        for name in ("change-plan", "runtime-probe"):
            self.write(
                f"skills/{name}/SKILL.md",
                f"---\nname: {name}\ndescription: Test {name} workflow.\n---\n\n"
                "Follow the current repository instructions.\n",
            )
        self.write(
            "agents/reviewer.toml",
            'name = "reviewer"\ndescription = "Review changes."\n'
            'developer_instructions = "Inspect changes without editing."\n',
        )
        self.write("references/checklist.md", "Check the actual requirements.\n")

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def catalog(self):
        self.write(
            "catalog.json",
            json.dumps({"schema_version": 1, "version": "0.1.0", "items": self.items}),
        )
        return Catalog(self.root)

    def test_selects_named_skills_and_transitive_dependencies_once(self):
        catalog = self.catalog()
        selected = catalog.select(
            skills=("change-plan",), agents=("reviewer",), groups=("core",)
        )
        self.assertEqual(set(selected), {"skill:change-plan", "agent:reviewer"})
        self.assertEqual(len(selected), 2)

    def test_selects_groups_and_all_items(self):
        catalog = self.catalog()
        self.assertEqual(catalog.select(groups=("ops",)), ["skill:runtime-probe"])
        self.assertEqual(set(catalog.select(all_items=True)), set(catalog.items))

    def test_unknown_selection_is_rejected(self):
        catalog = self.catalog()
        for selection in (
            {"skills": ("absent",)},
            {"agents": ("absent",)},
            {"groups": ("absent",)},
        ):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                catalog.select(**selection)

    def test_duplicate_ids_are_rejected(self):
        self.items.append(dict(self.items[0]))
        with self.assertRaises(ValueError):
            self.catalog()

    def test_missing_dependency_is_rejected(self):
        self.items[0]["dependencies"] = ["agent:absent"]
        with self.assertRaises(ValueError):
            self.catalog()

    def test_dependency_cycle_is_rejected(self):
        self.items[2]["dependencies"] = ["skill:change-plan"]
        with self.assertRaises(ValueError):
            self.catalog().select(skills=("change-plan",))

    def test_source_paths_cannot_escape_catalog(self):
        for unsafe in ("../outside", "/tmp/outside"):
            with self.subTest(path=unsafe):
                self.items[0]["path"] = unsafe
                with self.assertRaises(ValueError):
                    self.catalog()

    def test_resource_destinations_cannot_escape_installed_skill(self):
        for unsafe in ("../outside.md", "/tmp/outside.md"):
            with self.subTest(path=unsafe):
                self.items[0]["resources"] = {unsafe: "references/checklist.md"}
                with self.assertRaises(ValueError):
                    self.catalog()

    def test_resource_sources_cannot_escape_catalog(self):
        self.items[0]["resources"] = {"references/checklist.md": "../outside.md"}
        with self.assertRaises(ValueError):
            self.catalog()

    def test_missing_resource_is_rejected(self):
        self.items[0]["resources"] = {"references/checklist.md": "references/absent.md"}
        with self.assertRaises(ValueError):
            self.catalog()

    def test_resource_cannot_overwrite_skill_instructions(self):
        self.items[0]["resources"] = {"SKILL.md": "references/checklist.md"}
        with self.assertRaises(ValueError):
            self.catalog()

    def test_skill_metadata_must_match_catalog_identity(self):
        self.write(
            "skills/change-plan/SKILL.md",
            "---\nname: wrong-name\ndescription: A different skill.\n---\n",
        )
        with self.assertRaises(ValueError):
            self.catalog()

    def test_agent_metadata_must_match_catalog_identity(self):
        self.write(
            "agents/reviewer.toml",
            'name = "other_reviewer"\ndescription = "Review changes."\n'
            'developer_instructions = "Inspect changes without editing."\n',
        )
        with self.assertRaises(ValueError):
            self.catalog()

    def test_agent_requires_instructions(self):
        self.write(
            "agents/reviewer.toml",
            'name = "reviewer"\ndescription = "Review changes."\n',
        )
        with self.assertRaises(ValueError):
            self.catalog()


if __name__ == "__main__":
    unittest.main()
