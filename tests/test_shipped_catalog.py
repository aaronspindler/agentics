"""Check actual distributed capabilities, not only synthetic installer fixtures."""

import re
import unittest

import yaml

from agentics_tools.catalog import default_catalog
from agentics_tools.validation import validate


class ShippedCatalogTests(unittest.TestCase):
    def test_all_installed_markdown_links_resolve(self):
        validate(default_catalog())

    def test_skill_ui_metadata_and_invocation_policies_are_valid(self):
        catalog = default_catalog()
        for key, item in catalog.items.items():
            if item["kind"] != "skill":
                continue
            with self.subTest(skill=key):
                bundle = catalog.bundle(key)
                metadata = yaml.safe_load(bundle["agents/openai.yaml"][0])
                interface = metadata["interface"]
                self.assertIn(f"${item['name']}", interface["default_prompt"])
                self.assertTrue(25 <= len(interface["short_description"]) <= 64)
                if item["name"] == "pr-review":
                    self.assertIs(metadata["policy"]["allow_implicit_invocation"], False)
                header = re.match(r"---\n(.*?)\n---", bundle["SKILL.md"][0].decode(), re.S).group(1)
                frontmatter = yaml.safe_load(header)
                self.assertEqual(frontmatter["name"], item["name"])
                self.assertIsInstance(frontmatter["description"], str)

    def test_public_catalog_omits_workstation_paths_and_numeric_service_ids(self):
        catalog = default_catalog()
        # Keep the check itself publishable: never embed real private identifiers.
        private_metadata = re.compile(r"/(?:Users|home)/[^\s/]+|\b\d{12,20}\b")
        for key in catalog.items:
            for name, (contents, _) in catalog.bundle(key).items():
                with self.subTest(item=key, resource=name):
                    self.assertNotRegex(contents.decode(), private_metadata)
