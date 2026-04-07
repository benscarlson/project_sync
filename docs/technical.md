# Git Project Sync Technical Documentation

## Purpose

`project_sync.py` is a small command-line tool that applies a consistent git workflow to a list of local repositories defined in a config file.

## Architecture

The implementation lives in [src/project_sync.py](/Users/benc/projects/project_sync/src/project_sync.py) and is organized around a few small responsibilities:

- Argument parsing for the optional `--config` flag
- Repository config loading and validation
- Git command execution with consistent error handling
- Interactive prompting for staging and commit messages
- Per-repository workflow orchestration

## Configuration Model

The script expects a JSON file named `repos.json` by default. That file contains an array of objects with these fields:

- `name`: display name used in prompts and errors
- `path`: absolute or user-relative path to a local git repository

Validation performed during startup:

- The config file must exist
- The config file must be valid JSON
- The top-level JSON value must be an array
- Every entry must include non-empty `name` and `path` values
- Every `path` must exist and contain a `.git` directory

If validation fails, the script exits with a non-zero status and prints the error to stderr.

## Runtime Flow

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

After all repositories finish successfully, the script prints a summary table for the full run.

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
- `load_repos()`: parses and validates the config file
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
