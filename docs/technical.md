# Git Project Sync Technical Documentation

## Purpose

`reposync` is a small command-line tool that applies a consistent git workflow to a list of local repositories defined in a config file. Its Python implementation is `project_sync.py`.

## Architecture

The implementation lives in [src/project_sync.py](/Users/benc/projects/project_sync/src/project_sync.py) and is organized around a few small responsibilities:

- Argument parsing for `update` (the default), `add`, `remove`, and `list`, with optional `--config` and an `add`-only `--path` flag
- Repository config loading and validation
- Git command execution with consistent error handling
- Interactive prompting for staging and commit messages
- Per-repository workflow orchestration

## Configuration Model

The script expects a JSON file named `repos.json` by default. That file contains an array of objects with these fields:

- `name`: GitHub `owner/repository` name used in prompts, ordering, and summaries
- `path`: absolute or user-relative path to a local git repository

Config structure validation:

- The config file must exist
- The config file must be valid JSON
- The top-level JSON value must be an array
- Every entry must include non-empty `name` and `path` values

During synchronization, every `path` must also exist and contain a `.git` entry
(a directory or a worktree file). Config edits validate structure without requiring
existing entries to be available. `add` validates the new repository, rejects
duplicate names and paths, and inserts an entry alphabetically by name. `remove` deletes entries with
the requested name. Other fields and entries are preserved.

The positional argument to `add` is a repository path: `~` is expanded and
relative paths resolve from the caller's current directory. The resolved path is
stored with its GitHub `owner/repository` name, preferring the `origin` remote.
Without a GitHub remote, the directory name (or explicit `--path` name) is used.

If validation fails, the script exits with a non-zero status and prints the error to stderr.

## Runtime Flow

Repositories are sorted alphabetically by GitHub `owner/repository` before
processing; older configs also resolve owner prefixes from local remotes. Summary
rows are sorted independently by name.

For each configured repository:

1. Run `git status --short`
2. If the status is empty, run `git pull` and continue to the next repository
3. If local changes exist, display the status and prompt the user for `yes`, `no`, or `cancel`
4. If the user selects `yes`, run `git add -A`
5. Show status again after staging
6. Prompt for a commit message with `updates` as the default
7. Run `git commit -m <message>`
8. Run `git pull`
9. Stop execution if `git pull` fails
10. Run `git push` if the pull succeeds

After all repositories finish successfully, the script prints a summary table for the full run, followed by the local date and 24-hour time in the format `Tuesday, October 6, 2026 17:00`. This applies to both `reposync` and `reposync update`. Empty configs also produce a valid summary and timestamp.

`reposync` resolves symlinks, loads the project `.env` if present, and invokes
`project_sync.sh`, which defaults `--config` to the project's `repos.json`.
`add` and `remove` return after editing the config without running Git sync.

`list` loads the config and reads `git remote -v` locally for each available
repository. It prefers GitHub fetch URLs on `origin`, then other remotes, and
extracts `owner/repository` from HTTPS, SSH, or SCP-style URLs. The table contains
every configured path sorted alphabetically by GitHub name, using status labels when GitHub metadata is unavailable.
Both listing and sync summaries use `print_table()`. Sync summaries enable
`include_time` to print the local date and `HH:MM`; listing prints only the table.

## Error Handling

The script uses a dedicated `SyncError` exception to stop execution on operational failures.

Examples of stop conditions:

- Missing or malformed config
- A configured path that is not a git repository
- `git commit`, `git pull`, or `git push` returning a non-zero status
- User selecting `cancel`

`KeyboardInterrupt` is handled separately and exits with code `130`.

## Git Command Behavior

All git commands are executed with `subprocess.run()` using the repository path as the current working directory.

Implementation notes:

- Output is captured so failures can be surfaced clearly
- Most commands raise immediately on non-zero exit
- `pull`, `push`, and `commit` intentionally inspect the return code first so the tool can print command output before stopping

## Key Types And Functions

- `RepoConfig`: immutable repository config container
- `RepoSummary`: immutable result container for final reporting
- `SyncError`: workflow-level exception for controlled termination
- `load_config()`: parses and validates the config structure
- `load_repos()`: loads config entries and validates local repositories for sync
- `add_repo()` / `remove_repo()`: edit config entries
- `list_repos()`: displays GitHub repository names and absolute local paths
- `github_name_from_url()`: extracts the repository name from a GitHub remote URL
- `run_git()`: shared git subprocess wrapper
- `get_head_commit()`: reads the current repository `HEAD`
- `print_status()`: runs and displays `git status --short`
- `process_repo()`: implements the main workflow for one repository
- `print_summary_table()`: renders the final per-repository summary table
- `main()`: CLI entrypoint and process exit handling

## Constraints And Assumptions

- The tool assumes the target repositories already have remotes configured
- Merge issues are not auto-resolved; the script stops and requires manual intervention
- The script stages all local changes with `git add -A` when the user approves staging
- Pulled remote changes are detected by comparing `HEAD` before and after `git pull`
- The project currently uses only the Python standard library and does not add external dependencies
