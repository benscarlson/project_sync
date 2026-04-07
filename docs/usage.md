# Git Project Sync Usage

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
    "name": "project-a",
    "path": "/absolute/path/to/project-a"
  },
  {
    "name": "project-b",
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

Run the script from the project root:

```bash
python3 src/project_sync.py
```

To use a different config file:

```bash
python3 src/project_sync.py --config /path/to/repos.json
```

## Interactive Flow

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

## Notes

- Repository paths must already exist and contain a `.git` directory.
- The script stops on git command failures instead of attempting recovery.
- The script does not create repositories or initialize git remotes.
