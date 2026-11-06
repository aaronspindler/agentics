"""Exercise installation ownership and failures entirely in temporary homes."""

import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentics_tools.catalog import Catalog
from agentics_tools import installer
from agentics_tools.installer import Layout, install, status, uninstall, update


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agentics installer ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "catalog source"
        self.home = self.base / "user home"
        self.layout = Layout(self.home)
        self.items = [
            {
                "id": "skill:change-plan",
                "kind": "skill",
                "name": "change-plan",
                "path": "skills/change-plan",
                "group": "core",
                "dependencies": ["agent:reviewer"],
                "resources": {
                    "references/checklist.md": "references/checklist.md",
                    "scripts/check.py": "references/check.py",
                },
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
        self.write("references/check.py", "#!/usr/bin/env python3\nprint('checked')\n")
        (self.root / "references/check.py").chmod(0o755)
        self.catalog = self.reload_catalog()
        self.all_ids = self.catalog.select(all_items=True)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def reload_catalog(self):
        self.write(
            "catalog.json",
            json.dumps({"schema_version": 1, "version": "0.1.0", "items": self.items}),
        )
        return Catalog(self.root)

    def statuses(self, ids=None):
        return {entry["id"]: entry["status"] for entry in status(self.catalog, self.layout, ids)}

    def snapshot(self, path):
        if not path.exists():
            return None
        return {
            str(entry.relative_to(path)): (
                "symlink",
                str(entry.readlink()),
            )
            if entry.is_symlink()
            else (entry.read_bytes(), stat.S_IMODE(entry.stat().st_mode))
            for entry in path.rglob("*")
            if entry.is_file() or entry.is_symlink()
        }

    def test_install_bundles_resources_and_preserves_executability(self):
        install(self.catalog, self.layout, self.all_ids)
        skill = self.layout.skill_root / "change-plan"
        self.assertEqual(
            (skill / "references/checklist.md").read_text(),
            "Check the actual requirements.\n",
        )
        self.assertTrue((skill / "scripts/check.py").stat().st_mode & stat.S_IXUSR)
        self.assertTrue((self.layout.agent_root / "reviewer.toml").is_file())
        self.assertTrue(self.layout.state_path.is_file())
        self.assertEqual(set(self.statuses().values()), {"current"})

    def test_repeated_install_is_idempotent(self):
        install(self.catalog, self.layout, self.all_ids)
        before = self.snapshot(self.home)
        install(self.catalog, self.layout, self.all_ids)
        self.assertEqual(self.snapshot(self.home), before)

    def test_initial_dry_run_creates_no_home_or_manifest(self):
        actions = install(self.catalog, self.layout, self.all_ids, dry_run=True)
        self.assertEqual({action["id"] for action in actions}, set(self.all_ids))
        self.assertFalse(self.home.exists())

    def test_status_is_read_only_before_installation(self):
        self.assertEqual(set(self.statuses(self.all_ids).values()), {"not-installed"})
        self.assertFalse(self.home.exists())

    def test_skill_collision_preflights_all_items_without_writes(self):
        collision = self.layout.skill_root / "runtime-probe"
        collision.mkdir(parents=True)
        (collision / "SKILL.md").write_text("User-owned workflow.\n")
        before = self.snapshot(self.home)
        with self.assertRaises(ValueError):
            install(self.catalog, self.layout, self.all_ids)
        self.assertEqual(self.snapshot(self.home), before)
        self.assertEqual(self.statuses(["skill:runtime-probe"])["skill:runtime-probe"], "collision")

    def test_role_name_collision_under_different_filename_is_rejected(self):
        self.layout.agent_root.mkdir(parents=True)
        (self.layout.agent_root / "my-own-agent.toml").write_text(
            'name = "reviewer"\ndescription = "My reviewer."\n'
            'developer_instructions = "Review my changes."\n'
        )
        before = self.snapshot(self.home)
        with self.assertRaises(ValueError):
            install(self.catalog, self.layout, self.all_ids)
        self.assertEqual(self.snapshot(self.home), before)

    def test_explicit_global_role_registration_is_a_collision(self):
        codex_home = self.layout.agent_root.parent
        codex_home.mkdir(parents=True)
        (codex_home / "config.toml").write_text(
            '[agents.reviewer]\ndescription = "My reviewer."\n'
            'config_file = "elsewhere/my-reviewer.toml"\n'
        )
        before = self.snapshot(self.home)
        with self.assertRaises(ValueError):
            install(self.catalog, self.layout, self.all_ids)
        self.assertEqual(self.snapshot(self.home), before)

    def test_modified_skill_prevents_update_and_uninstall(self):
        install(self.catalog, self.layout, self.all_ids)
        installed = self.layout.skill_root / "change-plan/SKILL.md"
        installed.write_text(installed.read_text() + "Local customization.\n")
        self.assertEqual(self.statuses()["skill:change-plan"], "modified")
        before = self.snapshot(self.home)
        for operation in (update, uninstall):
            with self.subTest(operation=operation.__name__), self.assertRaises(ValueError):
                operation(self.catalog, self.layout, self.all_ids)
            self.assertEqual(self.snapshot(self.home), before)

    def test_added_missing_or_mode_changed_files_are_local_modifications(self):
        changes = ("extra", "missing", "mode")
        for index, change in enumerate(changes):
            with self.subTest(change=change):
                layout = Layout(self.base / f"variant home {index}")
                install(self.catalog, layout, ["skill:runtime-probe"])
                destination = layout.skill_root / "runtime-probe"
                if change == "extra":
                    (destination / "local-notes.md").write_text("Keep my notes.\n")
                elif change == "missing":
                    (destination / "SKILL.md").unlink()
                else:
                    (destination / "SKILL.md").chmod(0o755)
                before = self.snapshot(layout.skill_root.parent)
                self.assertEqual(
                    status(self.catalog, layout, ["skill:runtime-probe"])[0]["status"],
                    "modified",
                )
                with self.assertRaises(ValueError):
                    uninstall(self.catalog, layout, ["skill:runtime-probe"])
                self.assertEqual(self.snapshot(layout.skill_root.parent), before)

    def test_update_replaces_only_selected_installed_items(self):
        install(self.catalog, self.layout, self.all_ids)
        old_probe = (self.layout.skill_root / "runtime-probe/SKILL.md").read_bytes()
        self.write("references/checklist.md", "An updated checklist.\n")
        path = self.root / "skills/runtime-probe/SKILL.md"
        path.write_text(path.read_text() + "Updated probe guidance.\n")
        self.catalog = self.reload_catalog()
        self.assertEqual(self.statuses()["skill:change-plan"], "update-available")
        update(self.catalog, self.layout, ["skill:change-plan"])
        self.assertEqual(
            (self.layout.skill_root / "change-plan/references/checklist.md").read_text(),
            "An updated checklist.\n",
        )
        self.assertEqual((self.layout.skill_root / "runtime-probe/SKILL.md").read_bytes(), old_probe)
        self.assertEqual(self.statuses()["skill:runtime-probe"], "update-available")

    def test_role_source_filename_change_keeps_installed_state_consistent(self):
        install(self.catalog, self.layout, ["agent:reviewer"])
        original = self.root / "agents/reviewer.toml"
        original.rename(self.root / "agents/renamed-reviewer.toml")
        self.items[2]["path"] = "agents/renamed-reviewer.toml"
        self.catalog = self.reload_catalog()
        update(self.catalog, self.layout, ["agent:reviewer"])
        self.assertEqual(self.statuses(["agent:reviewer"])["agent:reviewer"], "current")
        definitions = list(self.layout.agent_root.glob("*.toml"))
        self.assertEqual(len(definitions), 1)
        uninstall(self.catalog, self.layout, ["agent:reviewer"])
        self.assertFalse(list(self.layout.agent_root.glob("*.toml")))

    def test_update_does_not_install_new_group_members(self):
        install(self.catalog, self.layout, ["skill:runtime-probe"])
        try:
            update(self.catalog, self.layout, self.all_ids)
        except ValueError:
            pass
        self.assertFalse((self.layout.skill_root / "change-plan").exists())
        self.assertFalse(self.layout.agent_root.exists())

    def test_catalog_group_changes_do_not_remove_installed_items(self):
        install(self.catalog, self.layout, self.all_ids)
        self.items[1]["group"] = "maintenance"
        self.catalog = self.reload_catalog()
        update(self.catalog, self.layout, self.catalog.select(groups=("core",)))
        self.assertTrue((self.layout.skill_root / "runtime-probe/SKILL.md").is_file())

    def test_update_refuses_removed_catalog_item_without_writes(self):
        install(self.catalog, self.layout, self.all_ids)
        self.items = [item for item in self.items if item["id"] != "skill:runtime-probe"]
        self.catalog = self.reload_catalog()
        before = self.snapshot(self.home)
        self.assertEqual(self.statuses()["skill:runtime-probe"], "source-unavailable")
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), self.assertRaisesRegex(
                ValueError, "Operation refused before writing:.*\n.*source unavailable"
            ):
                update(self.catalog, self.layout, self.all_ids, dry_run=dry_run)
            self.assertEqual(self.snapshot(self.home), before)

    def test_update_and_uninstall_dry_run_leave_existing_state_unchanged(self):
        install(self.catalog, self.layout, self.all_ids)
        self.write("references/checklist.md", "An updated checklist.\n")
        self.catalog = self.reload_catalog()
        before = self.snapshot(self.home)
        update(self.catalog, self.layout, self.all_ids, dry_run=True)
        self.assertEqual(self.snapshot(self.home), before)
        uninstall(self.catalog, self.layout, self.all_ids, dry_run=True)
        self.assertEqual(self.snapshot(self.home), before)

    def test_failed_replacement_restores_all_managed_items_and_state(self):
        install(self.catalog, self.layout, self.all_ids)
        before = self.snapshot(self.home)
        self.write("references/checklist.md", "An updated checklist.\n")
        probe = self.root / "skills/runtime-probe/SKILL.md"
        probe.write_text(probe.read_text() + "Updated probe guidance.\n")
        self.catalog = self.reload_catalog()
        original_rename = Path.rename

        def fail_second_replacement(path, target):
            if path.name == "payload" and Path(target).name == "runtime-probe":
                raise OSError("Simulated destination failure")
            return original_rename(path, target)

        with mock.patch.object(Path, "rename", fail_second_replacement):
            with self.assertRaises(OSError):
                update(self.catalog, self.layout, self.all_ids)
        self.assertEqual(self.snapshot(self.home), before)

    def test_incomplete_rollback_preserves_backups_and_restores_other_items(self):
        for failure in ("remove", "rename"):
            with self.subTest(failure=failure):
                layout = Layout(self.base / f"recovery home {failure}")
                install(self.catalog, layout, self.all_ids)
                change_plan = layout.skill_root / "change-plan"
                runtime_probe = layout.skill_root / "runtime-probe"
                before_change_plan = self.snapshot(change_plan)
                before_probe = self.snapshot(runtime_probe)
                before_state = layout.state_path.read_bytes()
                checklist = self.root / "references/checklist.md"
                checklist.write_text(checklist.read_text() + "Updated checklist.\n")
                probe_source = self.root / "skills/runtime-probe/SKILL.md"
                probe_source.write_text(probe_source.read_text() + "Updated probe.\n")
                self.catalog = self.reload_catalog()
                original_remove = installer._remove
                original_rename = Path.rename

                def fail_state_save(path, target):
                    raise OSError("Simulated state save failure")

                def fail_remove(path):
                    if failure == "remove" and path == runtime_probe:
                        raise OSError("Simulated rollback removal failure")
                    return original_remove(path)

                def fail_restore(path, target):
                    if failure == "rename" and path.name == "backup" and target == runtime_probe:
                        raise OSError("Simulated rollback rename failure")
                    return original_rename(path, target)

                with (
                    mock.patch.object(Path, "replace", fail_state_save),
                    mock.patch.object(installer, "_remove", fail_remove),
                    mock.patch.object(Path, "rename", fail_restore),
                    self.assertRaisesRegex(RuntimeError, "rollback incomplete") as error,
                ):
                    update(self.catalog, layout, self.all_ids)

                self.assertEqual(self.snapshot(change_plan), before_change_plan)
                self.assertEqual(layout.state_path.read_bytes(), before_state)
                backups = list(layout.skill_root.glob(".agentics-*/backup"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(self.snapshot(backups[0]), before_probe)
                self.assertIn(str(backups[0].parent), str(error.exception))
                lock = layout.state_path.with_suffix(".lock")
                self.assertTrue(lock.exists())
                self.assertIn(str(lock), str(error.exception))

    def test_state_temporary_path_cannot_overwrite_unrelated_symlink_target(self):
        install(self.catalog, self.layout, ["skill:runtime-probe"])
        outside = self.base / "unrelated-private-file.txt"
        outside.write_text("Preserve this unrelated file.\n")
        temporary_state = self.layout.state_path.with_suffix(".tmp")
        temporary_state.symlink_to(outside)
        source = self.root / "skills/runtime-probe/SKILL.md"
        source.write_text(source.read_text() + "Updated probe guidance.\n")
        self.catalog = self.reload_catalog()
        try:
            update(self.catalog, self.layout, ["skill:runtime-probe"])
        except ValueError:
            pass
        self.assertEqual(outside.read_text(), "Preserve this unrelated file.\n")
        self.assertTrue(temporary_state.is_symlink())

    def test_uninstall_cannot_leave_installed_dependent_without_required_agent(self):
        install(self.catalog, self.layout, self.all_ids)
        before = self.snapshot(self.home)
        with self.assertRaises(ValueError):
            uninstall(self.catalog, self.layout, ["agent:reviewer"])
        self.assertEqual(self.snapshot(self.home), before)

    def test_dependency_metadata_updates_are_used_for_uninstall_protection(self):
        install(self.catalog, self.layout, self.all_ids)
        self.items[0]["dependencies"].append("skill:runtime-probe")
        self.catalog = self.reload_catalog()
        update(self.catalog, self.layout, self.all_ids)
        before = self.snapshot(self.home)
        with self.assertRaises(ValueError):
            uninstall(self.catalog, self.layout, ["skill:runtime-probe"])
        self.assertEqual(self.snapshot(self.home), before)

    def test_uninstall_preserves_unrelated_skills_agents_and_config(self):
        install(self.catalog, self.layout, self.all_ids)
        unrelated_skill = self.layout.skill_root / "personal/SKILL.md"
        unrelated_skill.parent.mkdir()
        unrelated_skill.write_text("My skill.\n")
        unrelated_agent = self.layout.agent_root / "personal.toml"
        unrelated_agent.write_text('name = "personal"\n')
        config = self.layout.agent_root.parent / "config.toml"
        config.write_text('model = "my-model"\n')
        uninstall(self.catalog, self.layout, self.all_ids)
        self.assertEqual(unrelated_skill.read_text(), "My skill.\n")
        self.assertEqual(unrelated_agent.read_text(), 'name = "personal"\n')
        self.assertEqual(config.read_text(), 'model = "my-model"\n')
        self.assertFalse((self.layout.skill_root / "change-plan").exists())
        self.assertFalse((self.layout.agent_root / "reviewer.toml").exists())

    def test_custom_codex_home_keeps_standard_global_skill_location(self):
        custom = self.base / "custom codex configuration"
        layout = Layout(self.home, custom)
        install(self.catalog, layout, self.all_ids)
        self.assertEqual(layout.skill_root, self.home / ".agents/skills")
        self.assertEqual(layout.agent_root, custom / "agents")
        self.assertEqual(layout.state_path, custom / "agentics/installed.json")
        self.assertTrue((custom / "agents/reviewer.toml").is_file())
        self.assertFalse((self.home / ".codex").exists())

    def test_missing_installation_directory_is_reported_and_not_recreated_by_status(self):
        install(self.catalog, self.layout, ["skill:runtime-probe"])
        installed = self.layout.skill_root / "runtime-probe"
        (installed / "SKILL.md").unlink()
        installed.rmdir()
        self.assertEqual(self.statuses(["skill:runtime-probe"])["skill:runtime-probe"], "missing")
        self.assertFalse(installed.exists())

    def test_symlinked_install_destination_is_never_followed(self):
        outside = self.base / "outside"
        outside.mkdir()
        marker = outside / "keep.txt"
        marker.write_text("Leave this directory alone.\n")
        self.layout.skill_root.mkdir(parents=True)
        (self.layout.skill_root / "runtime-probe").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            install(self.catalog, self.layout, ["skill:runtime-probe"])
        self.assertEqual(marker.read_text(), "Leave this directory alone.\n")
        self.assertEqual(set(outside.iterdir()), {marker})

    def test_symlink_added_to_managed_skill_blocks_update(self):
        install(self.catalog, self.layout, ["skill:runtime-probe"])
        outside = self.base / "private.txt"
        outside.write_text("Private content.\n")
        (self.layout.skill_root / "runtime-probe/local-link").symlink_to(outside)
        with self.assertRaises(ValueError):
            update(self.catalog, self.layout, ["skill:runtime-probe"])
        self.assertEqual(outside.read_text(), "Private content.\n")

    def test_symlinked_catalog_resource_is_rejected(self):
        target = self.base / "outside-reference.md"
        target.write_text("Not part of this collection.\n")
        resource = self.root / "references/checklist.md"
        resource.unlink()
        resource.symlink_to(target)
        with self.assertRaises(ValueError):
            catalog = self.reload_catalog()
            install(catalog, self.layout, ["skill:change-plan"])
        self.assertFalse(self.home.exists())


if __name__ == "__main__":
    unittest.main()
