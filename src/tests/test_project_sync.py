import contextlib
import importlib.util
import io
import json
import os
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "project_sync.py"
spec = importlib.util.spec_from_file_location("project_sync", SOURCE)
sync = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sync
spec.loader.exec_module(sync)


class ConfigCommandsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project_sync"
        self.project.mkdir()
        self.config = self.project / "repos.json"
        self.repo = self.root / "example"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.repo)], check=True)

    def read_config(self):
        return json.loads(self.config.read_text())

    def test_add_absolute_path_and_remove_without_running_sync(self):
        for command in ("add", "remove"):
            argument = str(self.repo) if command == "add" else "example"
            with patch.object(sys, "argv", ["reposync", command, argument, "--config", str(self.config)]), patch.object(sync, "process_repo") as process, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sync.main(), 0)
                process.assert_not_called()
            if command == "add":
                self.assertEqual(self.read_config(), [{"name": "example", "path": str(self.repo.resolve())}])
            else:
                self.assertEqual(self.read_config(), [])

    def test_explicit_path_preserves_unavailable_entries(self):
        original = [{"name": "missing", "path": str(self.root / "missing"), "extra": 1}]
        self.config.write_text(json.dumps(original))
        sync.add_repo(self.config, "custom", str(self.repo))
        self.assertIn(original[0], self.read_config())
        sync.remove_repo(self.config, "missing")
        self.assertEqual([entry["name"] for entry in self.read_config()], ["custom"])

    def test_invalid_add_and_duplicates_do_not_change_config(self):
        sync.add_repo(self.config, str(self.repo))
        before = self.config.read_bytes()
        for name, path in ((str(self.repo), None), ("alias", str(self.repo)), (str(self.root / "missing"), None), ("nongit", str(self.project))):
            with self.subTest(name=name), self.assertRaises(sync.SyncError):
                sync.add_repo(self.config, name, path)
            self.assertEqual(self.config.read_bytes(), before)
        with self.assertRaises(sync.SyncError):
            sync.remove_repo(self.config, "unknown")
        self.assertEqual(self.config.read_bytes(), before)

    def test_does_not_substitute_nested_src_directory(self):
        nested = self.root / "nested" / "src"
        nested.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet", str(nested)], check=True)
        with self.assertRaises(sync.SyncError):
            sync.add_repo(self.config, str(nested.parent))
        self.assertFalse(self.config.exists())

    def test_relative_path_from_caller_through_symlink(self):
        command = self.root / "reposync"
        command.symlink_to(SOURCE.parents[1] / "reposync")
        result = subprocess.run(
            [str(command), "add", "example", "--config", str(self.config)],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_config(), [{"name": "example", "path": str(self.repo.resolve())}])

    def test_tilde_path_expansion(self):
        with patch.dict(os.environ, {"HOME": str(self.root)}):
            sync.add_repo(self.config, "~/example")
        self.assertEqual(self.read_config()[0], {"name": "example", "path": str(self.repo.resolve())})

    def test_default_and_explicit_update_use_same_workflow(self):
        self.config.write_text("[]")
        for args in ([], ["update"]):
            output = io.StringIO()
            with patch.object(sys, "argv", ["reposync", *args, "--config", str(self.config)]), patch.object(sync, "load_repos", return_value=[sync.RepoConfig("example", self.repo)]), patch.object(sync, "process_repo", return_value=sync.RepoSummary("example", False, False, "n/a")) as process, patch.object(sync, "datetime") as date, contextlib.redirect_stdout(output):
                date.now.return_value = datetime(2026, 10, 6, 17, 0)
                self.assertEqual(sync.main(), 0)
                process.assert_called_once()
            self.assertIn("Tuesday, October 6, 2026 17:00", output.getvalue())

    def test_summary_date_and_empty_config(self):
        for summaries in ([], [sync.RepoSummary("example", True, False, "committed")]):
            output = io.StringIO()
            with patch.object(sync, "datetime") as date, contextlib.redirect_stdout(output):
                date.now.return_value = datetime(2026, 10, 6, 17, 0)
                sync.print_summary_table(summaries)
            self.assertEqual(output.getvalue().splitlines()[-1], "Tuesday, October 6, 2026 17:00")

    def test_invalid_command_arguments(self):
        for args in (["add"], ["remove"], ["update", "example"], ["list", "example"], ["list", "--path", str(self.repo)], ["remove", "example", "--path", str(self.repo)]):
            with self.subTest(args=args), patch.object(sys, "argv", ["reposync", *args]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                sync.parse_args()
            self.assertEqual(error.exception.code, 2)

    def test_github_remote_url_formats(self):
        for url in (
            "git@github.com:benscarlson/myrepo.git",
            "https://github.com/benscarlson/myrepo.git",
            "ssh://git@github.com/benscarlson/myrepo.git",
            "ssh://git@github.com:22/benscarlson/myrepo",
            "https://github.com/benscarlson/myrepo/",
        ):
            with self.subTest(url=url):
                self.assertEqual(sync.github_name_from_url(url), "benscarlson/myrepo")
        for url in ("https://gitlab.com/owner/repo.git", "https://github.com/owner", "https://github.com/owner/repo/extra", "git@fakegithub.com:owner/repo.git", "/local/repo"):
            with self.subTest(url=url):
                self.assertIsNone(sync.github_name_from_url(url))

    def test_list_prefers_origin_and_preserves_config(self):
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "aaa", "https://github.com/other/fork.git"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "git@github.com:benscarlson/myrepo.git"], check=True)
        self.config.write_text(json.dumps([{"name": "example", "path": str(self.repo)}]))
        before = self.config.read_bytes()
        output = io.StringIO()
        with patch.object(sys, "argv", ["reposync", "list", "--config", str(self.config)]), patch.object(sync, "process_repo") as process, patch.object(sync, "datetime") as date, contextlib.redirect_stdout(output):
            date.now.return_value = datetime(2026, 10, 6, 17, 0)
            self.assertEqual(sync.main(), 0)
            process.assert_not_called()
            date.now.assert_not_called()
        self.assertIn("benscarlson/myrepo", output.getvalue())
        self.assertNotIn("other/fork", output.getvalue())
        self.assertIn(str(self.repo.resolve()), output.getvalue())
        self.assertNotIn("Tuesday, October 6, 2026", output.getvalue())
        self.assertIn("benscarlson/myrepo", output.getvalue().splitlines()[-1])
        self.assertEqual(self.config.read_bytes(), before)

    def test_list_missing_repositories_and_fallback_remote(self):
        self.config.write_text(json.dumps([
            {"name": "example", "path": str(self.repo)},
            {"name": "missing", "path": str(self.root / "missing")},
        ]))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.list_repos(self.config)
        self.assertIn("No GitHub remote", output.getvalue())
        self.assertIn("Unavailable", output.getvalue())
        self.assertIn(str((self.root / "missing").resolve()), output.getvalue())
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "upstream", "https://github.com/owner/upstream.git"], check=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.list_repos(self.config)
        self.assertIn("owner/upstream", output.getvalue())

    def test_list_empty_config(self):
        self.config.write_text("[]")
        output = io.StringIO()
        with patch.object(sync, "datetime") as date, contextlib.redirect_stdout(output):
            sync.list_repos(self.config)
            date.now.assert_not_called()
        self.assertIn("GitHub Repository", output.getvalue())
        self.assertIn("Local Path", output.getvalue())

    def test_add_github_name_and_alphabetical_insertion(self):
        self.config.write_text(json.dumps([
            {"name": "ycrc/zebra", "path": str(self.root / "zebra")},
            {"name": "benscarlson/aaa", "path": str(self.root / "aaa")},
        ]))
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "git@github.com:benscarlson/llm.git"], check=True)
        sync.add_repo(self.config, str(self.repo))
        self.assertEqual([item["name"] for item in self.read_config()], ["benscarlson/aaa", "benscarlson/llm", "ycrc/zebra"])
        sync.remove_repo(self.config, "benscarlson/llm")
        self.assertEqual(len(self.read_config()), 2)

    def test_update_and_list_sort_by_github_owner_and_name(self):
        second = self.root / "second"
        subprocess.run(["git", "init", "--quiet", str(second)], check=True)
        for path, name in ((self.repo, "ycrc/aaa"), (second, "benscarlson/bbb")):
            subprocess.run(["git", "-C", str(path), "remote", "add", "origin", f"https://github.com/{name}.git"], check=True)
        self.config.write_text(json.dumps([
            {"name": "aaa", "path": str(self.repo)},
            {"name": "bbb", "path": str(second)},
        ]))
        self.assertEqual([repo.name for repo in sync.load_repos(self.config)], ["benscarlson/bbb", "ycrc/aaa"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.list_repos(self.config)
        self.assertLess(output.getvalue().index("benscarlson/bbb"), output.getvalue().index("ycrc/aaa"))
        with patch.object(sys, "argv", ["reposync", "update", "--config", str(self.config)]), patch.object(sync, "process_repo") as process, contextlib.redirect_stdout(io.StringIO()):
            process.side_effect = lambda repo: sync.RepoSummary(repo.name, False, False, "n/a")
            self.assertEqual(sync.main(), 0)
            self.assertEqual([call.args[0].name for call in process.call_args_list], ["benscarlson/bbb", "ycrc/aaa"])

    def test_summary_sorts_names_independently(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sync.print_summary_table([
                sync.RepoSummary("ycrc/aaa", False, False, "n/a"),
                sync.RepoSummary("benscarlson/bbb", False, False, "n/a"),
            ])
        self.assertLess(output.getvalue().index("benscarlson/bbb"), output.getvalue().index("ycrc/aaa"))


if __name__ == "__main__":
    unittest.main()
