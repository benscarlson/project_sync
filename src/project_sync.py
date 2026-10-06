#!/usr/bin/env python3
"""Synchronize multiple git repositories from a simple config file."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_COMMIT_MESSAGE = "updates"


@dataclass(frozen=True)
class RepoConfig:
    """Configuration for a single repository."""

    name: str
    path: Path


@dataclass(frozen=True)
class RepoSummary:
    """Summary of what happened for one repository."""

    name: str
    had_local_changes: bool
    pulled_changes: bool
    commit_status: str


class SyncError(RuntimeError):
    """Raised when synchronization should stop."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reposync",
        description="Automate git status/add/commit/pull/push for multiple repositories.",
    )
    parser.add_argument("command", nargs="?", choices=("update", "add", "remove", "list"), default="update")
    parser.add_argument("name", nargs="?", help="Repository path to add, or configured name to remove.")
    parser.add_argument("--path", help="Local repository path for add when supplying a custom name.")
    parser.add_argument(
        "--config",
        default="repos.json",
        help='Path to the repository config file (default: "repos.json").',
    )
    args = parser.parse_args()
    if args.command in {"add", "remove"} and (not args.name or not args.name.strip()):
        parser.error(f"{args.command} requires a repository {'path' if args.command == 'add' else 'name'}")
    if args.command in {"update", "list"} and args.name is not None:
        parser.error(f"{args.command} does not accept a repository name")
    if args.path is not None and args.command != "add":
        parser.error("--path can only be used with add")
    return args


def load_config(config_path: Path) -> list[dict[str, Any]]:
    if not config_path.exists():
        raise SyncError(
            f'Config file "{config_path}" was not found. Copy "repos_example.json" to "repos.json" and edit it.'
        )

    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f'Config file "{config_path}" is not valid JSON: {exc}') from exc

    if not isinstance(raw_config, list):
        raise SyncError('Config file must contain a JSON array of repositories.')

    for index, item in enumerate(raw_config, start=1):
        if not isinstance(item, dict):
            raise SyncError(f"Repository entry #{index} must be a JSON object.")

        name = item.get("name")
        path_value = item.get("path")
        if not isinstance(name, str) or not name.strip():
            raise SyncError(f'Repository entry #{index} is missing a valid "name".')
        if not isinstance(path_value, str) or not path_value.strip():
            raise SyncError(f'Repository entry #{index} is missing a valid "path".')

    return raw_config


def validate_repo(name: str, repo_path: Path) -> None:
    if not repo_path.exists():
        raise SyncError(f'Repository "{name}" path does not exist: {repo_path}')
    if not (repo_path / ".git").exists():
        raise SyncError(f'Repository "{name}" is not a git repository: {repo_path}')


def load_repos(config_path: Path) -> list[RepoConfig]:
    repos: list[RepoConfig] = []
    for item in load_config(config_path):
        name = item["name"]
        path_value = item["path"]
        repo_path = Path(path_value).expanduser().resolve()
        validate_repo(name, repo_path)
        repo = RepoConfig(name=name.strip(), path=repo_path)
        repos.append(RepoConfig(name=get_github_repo_name(repo) or repo.name, path=repo_path))

    return sorted(repos, key=lambda repo: repo.name.casefold())


def add_repo(config_path: Path, name: str, path: str | None = None) -> None:
    repo_path = Path(path if path is not None else name).expanduser().resolve()
    name = name.strip() if path is not None else repo_path.name
    entries = load_config(config_path) if config_path.exists() else []
    validate_repo(name, repo_path)
    name = get_github_repo_name(RepoConfig(name, repo_path)) or name
    if any(item["name"].strip() == name for item in entries):
        raise SyncError(f'Repository "{name}" is already configured.')
    if any(Path(item["path"]).expanduser().resolve() == repo_path for item in entries):
        raise SyncError(f'Repository path "{repo_path}" is already configured.')
    entries.append({"name": name, "path": str(repo_path)})
    entries.sort(key=lambda item: item["name"].strip().casefold())
    config_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f'Added "{name}" ({repo_path}) to {config_path}.')


def remove_repo(config_path: Path, name: str) -> None:
    name = name.strip()
    entries = load_config(config_path)
    remaining = [item for item in entries if item["name"].strip() != name]
    if len(remaining) == len(entries):
        raise SyncError(f'Repository "{name}" is not configured.')
    config_path.write_text(json.dumps(remaining, indent=2) + "\n", encoding="utf-8")
    print(f'Removed "{name}" from {config_path}.')


def run_git(
    repo: RepoConfig,
    *args: str,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    result = subprocess.run(
        command,
        cwd=repo.path,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if check and result.returncode != 0:
        command_text = " ".join(command)
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise SyncError(f'[{repo.name}] "{command_text}" failed: {message}')
    return result


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def get_head_commit(repo: RepoConfig) -> str:
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


def print_status(repo: RepoConfig) -> str:
    result = run_git(repo, "status", "--short")
    status = result.stdout.strip()
    print_section(f"{repo.name}: git status")
    print(status if status else "Working tree clean")
    return status


def ask_yes_no_cancel(repo: RepoConfig) -> str:
    while True:
        answer = input(f"[{repo.name}] Add changed items? (yes/no/cancel): ").strip().lower()
        if answer in {"yes", "y"}:
            return "yes"
        if answer in {"no", "n"}:
            return "no"
        if answer in {"cancel", "c"}:
            return "cancel"
        print('Please respond with "yes", "no", or "cancel".')


def ask_commit_message(repo: RepoConfig) -> str:
    prompt = f'[{repo.name}] Commit message [{DEFAULT_COMMIT_MESSAGE}]: '
    message = input(prompt).strip()
    return message or DEFAULT_COMMIT_MESSAGE


def pull_repo(repo: RepoConfig) -> bool:
    print(f'[{repo.name}] Running "git pull"...')
    before_head = get_head_commit(repo)
    result = run_git(repo, "pull", check=False)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    if result.returncode != 0:
        raise SyncError(
            f"[{repo.name}] git pull reported an error. Resolve merge issues before continuing."
        )
    after_head = get_head_commit(repo)
    return before_head != after_head


def push_repo(repo: RepoConfig) -> None:
    print(f'[{repo.name}] Running "git push"...')
    result = run_git(repo, "push", check=False)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    if result.returncode != 0:
        raise SyncError(f"[{repo.name}] git push failed.")


def commit_repo(repo: RepoConfig, message: str) -> None:
    print(f'[{repo.name}] Creating commit...')
    result = run_git(repo, "commit", "-m", message, check=False)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    if result.returncode != 0:
        raise SyncError(f"[{repo.name}] git commit failed.")


def stage_changes(repo: RepoConfig) -> None:
    print(f'[{repo.name}] Running "git add -A"...')
    run_git(repo, "add", "-A")


def process_repo(repo: RepoConfig) -> RepoSummary:
    status = print_status(repo)

    if not status:
        print(f'[{repo.name}] No local updates detected. Pulling latest changes and moving on.')
        pulled_changes = pull_repo(repo)
        return RepoSummary(
            name=repo.name,
            had_local_changes=False,
            pulled_changes=pulled_changes,
            commit_status="n/a",
        )

    action = ask_yes_no_cancel(repo)
    if action == "cancel":
        raise SyncError(f"[{repo.name}] User canceled execution.")
    if action == "no":
        print(f'[{repo.name}] Skipping repository.')
        return RepoSummary(
            name=repo.name,
            had_local_changes=True,
            pulled_changes=False,
            commit_status="skipped",
        )

    stage_changes(repo)
    print_status(repo)
    commit_message = ask_commit_message(repo)
    commit_repo(repo, commit_message)
    pulled_changes = pull_repo(repo)
    push_repo(repo)
    return RepoSummary(
        name=repo.name,
        had_local_changes=True,
        pulled_changes=pulled_changes,
        commit_status="committed",
    )


def print_summary_table(summaries: list[RepoSummary]) -> None:
    headers = ["Repository", "Local Changes", "Pulled Changes", "Committed/Skipped"]
    rows = [
        [
            summary.name,
            "yes" if summary.had_local_changes else "no",
            "yes" if summary.pulled_changes else "no",
            summary.commit_status,
        ]
        for summary in sorted(summaries, key=lambda summary: summary.name.casefold())
    ]
    print_table("Summary", headers, rows, include_time=True)


def print_table(
    title: str, headers: list[str], rows: list[list[str]], *, include_time: bool = False
) -> None:
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]

    def format_row(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    separator = "-+-".join("-" * width for width in widths)

    print_section(title)
    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))
    if include_time:
        today = datetime.now()
        timestamp = f"{today.strftime('%A, %B')} {today.day}, {today.year}"
        timestamp += today.strftime(" %H:%M")
        print(f"\n{timestamp}")


def github_name_from_url(url: str) -> str | None:
    if "://" not in url:
        # Git's SCP-style SSH URL: git@github.com:owner/repository.git.
        host, separator, path = url.partition(":")
        if not separator or host.rsplit("@", 1)[-1].lower() != "github.com":
            return None
    else:
        parsed = urlparse(url)
        if parsed.hostname != "github.com":
            return None
        path = parsed.path
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    return path if len(parts) == 2 and all(parts) else None


def get_github_repo_name(repo: RepoConfig) -> str | None:
    result = run_git(repo, "remote", "-v", check=False)
    if result.returncode != 0:
        return None
    remotes = [line.split() for line in result.stdout.splitlines()]
    remotes.sort(key=lambda remote: remote[0] != "origin" if remote else True)
    for remote in remotes:
        if len(remote) == 3 and remote[2] == "(fetch)":
            name = github_name_from_url(remote[1])
            if name:
                return name
    return None


def list_repos(config_path: Path) -> None:
    rows: list[list[str]] = []
    for item in load_config(config_path):
        repo = RepoConfig(item["name"].strip(), Path(item["path"]).expanduser().resolve())
        github_name = "Unavailable"
        if repo.path.is_dir() and (repo.path / ".git").exists():
            github_name = get_github_repo_name(repo) or "No GitHub remote"
        rows.append([github_name, str(repo.path)])
    rows.sort(key=lambda row: (row[0].casefold(), row[1].casefold()))
    print_table("Repositories", ["GitHub Repository", "Local Path"], rows)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()

    try:
        if args.command == "list":
            list_repos(config_path)
            return 0
        if args.command == "add":
            add_repo(config_path, args.name, args.path)
            return 0
        if args.command == "remove":
            remove_repo(config_path, args.name)
            return 0
        repos = load_repos(config_path)
        summaries: list[RepoSummary] = []
        for repo in repos:
            summaries.append(process_repo(repo))
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.", file=sys.stderr)
        return 130
    except (SyncError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print_summary_table(summaries)
    print("\nAll repositories processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
