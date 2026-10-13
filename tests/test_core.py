import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from gmrecover.core import Workspace, audit_workspace, extract_artifact, inspect_artifact, render_report
from gmrecover.pipeline import run_pipeline
from gmrecover.sweep import discover_candidates, run_sweep
from gmrecover.manuals import _canonical_url, import_manual, index_manual, source_catalog


class RecoveryPipelineTests(unittest.TestCase):
    def test_source_tree_pipeline_and_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "game.yyp").write_text("{}", encoding="utf-8")
            (source / "player.gml").write_text("image_xscale = -1; place_meeting(x, y, obj_wall);", encoding="utf-8")
            workspace = Workspace(root / "work")
            details = inspect_artifact(source, workspace)
            self.assertEqual(details["kind"], "modern-gamemaker-source")
            extracted = extract_artifact(workspace)
            self.assertEqual(extracted["adapter"], "source-tree")
            self.assertEqual(extract_artifact(workspace)["adapter"], "source-tree")
            audit = audit_workspace(workspace, Path(extracted["output"]))
            self.assertEqual(audit["files_scanned"], 1)
            self.assertGreaterEqual(len(audit["findings"]), 2)
            markdown, report_html = render_report(workspace)
            self.assertTrue(markdown.is_file())
            self.assertTrue(report_html.is_file())
            manifest = json.loads(workspace.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["stages"]["report"]["status"], "complete")
            self.assertIn("| report | complete |", markdown.read_text(encoding="utf-8"))

    def test_zip_slip_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escape.txt", "no")
            workspace = Workspace(root / "work")
            inspect_artifact(archive_path, workspace)
            with self.assertRaisesRegex(ValueError, "escapes destination"):
                extract_artifact(workspace)
            self.assertFalse((root / "escape.txt").exists())

    def test_executable_is_never_run_and_records_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "old-game.exe"
            executable.write_bytes(b"MZ" + b"\0" * 32)
            workspace = Workspace(root / "work")
            inspect_artifact(executable, workspace)
            result = extract_artifact(workspace)
            self.assertIsNone(result["adapter"])
            self.assertEqual(workspace.load()["stages"]["extract"]["status"], "blocked")

    def test_pipeline_runs_without_a_shell_and_resumes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = Workspace(root / "work")
            workspace.ensure()
            config = root / "pipeline.toml"
            config.write_text(
                "[stages.normalize]\n"
                f"command = [{json.dumps(sys.executable)}, \"-c\", \"from pathlib import Path; Path(r'{workspace.root}/normalized/done').write_text('ok')\"]\n",
                encoding="utf-8",
            )
            first = run_pipeline(workspace, config)
            self.assertEqual(first["normalize"]["status"], "complete")
            self.assertTrue((workspace.root / "normalized" / "done").is_file())
            second = run_pipeline(workspace, config)
            self.assertTrue(second["normalize"]["resumed"])

    def test_sweep_discovers_by_format_and_ignores_unrelated_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "game.gmk").write_bytes(b"source")
            with zipfile.ZipFile(root / "game.zip", "w") as archive:
                archive.writestr("project/game.yyp", "{}")
            with zipfile.ZipFile(root / "photos.zip", "w") as archive:
                archive.writestr("photo.jpg", b"jpeg")
            candidates = discover_candidates(root)
            self.assertEqual([item.path.name for item in candidates], ["game.gmk", "game.zip"])

    def test_sweep_runs_safe_passes_and_reports_blockers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "game.yyp").write_text("{}", encoding="utf-8")
            (source / "player.gml").write_text("draw_text(x, y, 'hello');", encoding="utf-8")
            result = run_sweep(source, root / "workspaces")
            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(result["results"][0]["status"], "complete")
            self.assertTrue(Path(result["results"][0]["reports"][0]).is_file())

    def test_manual_index_contains_facts_and_citations_without_prose(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manual = root / "manual"
            manual.mkdir()
            (manual / "draw_text.html").write_text(
                "<h1>draw_text</h1><p>Copyrighted explanatory paragraph.</p>"
                "<code>draw_text(x, y, string)</code><pre>if (ready) draw_text(0, 0, name);</pre>",
                encoding="utf-8",
            )
            cache = root / "cache"
            imported = import_manual("fixture-gm8", manual, cache)
            self.assertEqual(imported["documents"], 1)
            output = root / "facts.json"
            indexed = index_manual("fixture-gm8", cache, output)
            self.assertGreaterEqual(indexed["symbols"], 1)
            facts = json.loads(output.read_text(encoding="utf-8"))
            draw = next(item for item in facts["symbols"] if item["name"] == "draw_text")
            self.assertIn("draw_text(x, y, string)", draw["signatures"])
            self.assertTrue(draw["citations"])
            self.assertNotIn("Copyrighted explanatory paragraph", output.read_text(encoding="utf-8"))
            self.assertIn("current-lts", source_catalog()["official_sources"])
            self.assertFalse(source_catalog()["historical_sources"]["gms14"]["automatic_fetch"])
            self.assertIn("Instance%20Keywords", _canonical_url("https://example.test/Instance Keywords/self.htm#topic"))


if __name__ == "__main__":
    unittest.main()
