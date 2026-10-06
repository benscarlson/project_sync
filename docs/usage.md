# Reposync Usage

## Overview

`src/project_sync.py` automates a standard git workflow across multiple repositories:

- Check local status
- Pull when the repository is clean
- Prompt before staging local changes
- Commit staged changes with a default message of `updates`
- Pull remote changes
- Stop if pull introduces merge issues
- Push when the pull succeeds

## Configuration

Create a file named `repos.json` in the project root. The file should contain a JSON array of repositories:

```json
[
  {
    "name": "your-org/project-a",
    "path": "/absolute/path/to/project-a"
  },
  {
    "name": "your-org/project-b",
    "path": "/absolute/path/to/project-b"
  }
]
```

An example file is provided at `repos_example.json`.

## Git Setup

The script assumes each configured path already points to a working local git repository. Before using the script, make sure the following setup is complete for every repository you list in `repos.json`.

Configure your git identity if you have not done that already:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

If the repository already exists on GitHub, clone it locally first:

```bash
git clone git@github.com:your-org/your-repo.git
```

If the repository does not exist locally yet and you are starting from an existing project directory, initialize git and connect it to a remote:

```bash
cd /path/to/project
git init
git remote add origin git@github.com:your-org/your-repo.git
```

If the remote default branch should be `main`, you can ensure that locally with:

```bash
git branch -M main
```

Before relying on the script, verify that each repository can talk to its remote normally:

```bash
git -C /path/to/project remote -v
git -C /path/to/project pull
git -C /path/to/project push
```

If `git pull` or `git push` fails from the command line, the script will fail the same way. Resolve authentication, remote, or branch-tracking issues first.

## Running the Script

Run the command wrapper from the project root:

```bash
./reposync
```

To make the command available from any directory, link the wrapper script into `~/bin`:

```bash
ln -s /path/to/project_sync/reposync ~/bin/reposync
```

Then run:

```bash
reposync
# Equivalent explicit command:
reposync update
```

The wrapper loads environment variables from `.env` in the project root if that file exists, then runs `project_sync.sh`. The shell script executes the Python application with the project root `repos.json` file.

You can still run the Python script directly from the project root:

```bash
python3 src/project_sync.py
```

To use a different config file:

```bash
reposync --config /path/to/repos.json
```

## Adding and Removing Repositories

```bash
reposync add ~/projects/project-a
reposync remove your-org/project-a
```

`add` accepts an absolute path, a path beginning with `~`, or a path relative to
the current working directory. For example, when running from `~/projects`,
`reposync add project-a` adds `~/projects/project-a`. The config stores the
resolved absolute path and uses the GitHub `owner/repository` name from local
remotes, preferring `origin`. New entries are inserted alphabetically by name.
Quote paths containing spaces. For repositories without a GitHub remote, the
directory name is used; supply `--path` to set a fallback name:

```bash
reposync add "~/Documents/Obsidian Vault"
reposync add notes --path "$HOME/Documents/Obsidian Vault"
reposync add project-a --path /path/to/project-a --config /path/to/repos.json
```

Repository paths resolve from the current directory even with a custom config
or a symlinked wrapper. Adding requires an existing
local Git repository and rejects duplicate names or paths. It creates the config
if it is missing. Removing deletes only the matching config entry; it leaves the
repository on disk. Both commands preserve other entries and do not synchronize
repositories. Removing also works when a configured repository no longer exists.

The original `project_sync` wrapper remains available for compatibility.

## Listing Repositories

```bash
reposync list
reposync list --config /path/to/repos.json
```

The command prints a table with the GitHub repository name (for example,
`benscarlson/myrepo`) and the full absolute local path, without a date or time.
Rows are sorted alphabetically by GitHub name. It reads local Git remotes, preferring `origin`, and supports HTTPS and SSH
GitHub URLs. Entries without a GitHub remote show `No GitHub remote`; missing
or unreadable repositories show `Unavailable`. Every configured entry remains
in the table. Listing does not change the config or synchronize repositories.

## Interactive Flow

Repositories are processed alphabetically by `owner/repository`. The summary
table uses the same order and includes the owner prefix.

For each repository:

1. The script runs `git status --short`.
2. If the repository is clean, the script runs `git pull` and moves to the next repository.
3. If local changes exist, the script shows the status and asks:

```text
Add changed items? (yes/no/cancel)
```

Response behavior:

- `yes`: run `git add -A` and continue
- `no`: skip that repository
- `cancel`: stop the full program immediately

If you continue:

1. The script shows `git status --short` again after staging.
2. The script prompts for a commit message:

```text
Commit message [updates]:
```

3. Press `Enter` to use `updates`, or type a custom message.
4. The script runs `git commit -m <message>`.
5. The script runs `git pull`.
6. If `git pull` fails, execution stops so merge issues can be resolved manually.
7. If `git pull` succeeds, the script runs `git push`.

After all repositories are processed successfully, the script prints a small summary table showing:

- whether each repository had local changes
- whether `git pull` brought in remote changes
- whether local changes were committed or skipped

Immediately after the update summary table, `reposync` and `reposync update`
print the local date and time using a 24-hour clock, for example
`Tuesday, October 6, 2026 17:00`. `reposync list` prints no date or time.

## Notes

- Repository paths must already exist and contain a `.git` directory.
- The script stops on git command failures instead of attempting recovery.
- The script does not create repositories or initialize git remotes.
