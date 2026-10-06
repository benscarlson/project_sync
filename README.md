# Reposync

Synchronize multiple local Git repositories with an interactive command that
checks status, prompts before staging and committing changes, pulls, and pushes.
Each synchronization run ends with a summary table and the local date and time
(for example, `Tuesday, October 6, 2026 17:00`). `reposync list` prints only the
repository table, without a date or time.

## Installation

Requires Python 3.10 or later and command-line Git. No additional Python packages
are needed. Each repository must already be configured for `git pull` and
`git push`.

Create `~/bin` if needed and link the command so it can run from any directory:

```bash
mkdir -p ~/bin
ln -s /Users/benc/projects/project_sync/reposync ~/bin/reposync
```

If you keep this project elsewhere, replace the source path with the absolute
path to its `reposync` script.

Make sure `~/bin` is on your `PATH`. For zsh, add this line to `~/.zshrc` if it is
not already configured:

```bash
export PATH="$HOME/bin:$PATH"
```

Open a new terminal or run `source ~/.zshrc`, then verify the command:

```bash
reposync --help
```

The wrapper loads the project's `.env` file if present and uses the project's
`repos.json`, even when called from another directory.

## Usage

```bash
reposync                             # Synchronize configured repositories
reposync update                      # Same as reposync
reposync add ~/projects/myrepo        # Add an existing local repository
reposync remove owner/myrepo               # Remove its config entry
reposync list                        # Show GitHub names and full local paths
reposync --config /path/to/repos.json # Use another config file
```

`add` accepts absolute paths, `~` paths, and paths relative to the current
directory. It stores the absolute path and the GitHub `owner/repository` name from local
remotes, preferring `origin`. Repositories without a GitHub remote use the
directory name, or the name supplied with `reposync add myname --path /path/to/repo`.
Entries are inserted alphabetically by name. Removing an entry leaves the repository
on disk.

Synchronization, summary tables, and listings are sorted alphabetically by
`owner/repository`. Configuration lives in `repos.json`; see `repos_example.json` for its format.
During synchronization, clean repositories are pulled. For repositories with
local changes, you can stage and commit, skip, or cancel. The default commit
message is `updates`. Git failures stop the run so you can resolve them.

See [the usage guide](docs/usage.md) for configuration and Git setup, and
[the technical documentation](docs/technical.md) for implementation details.
