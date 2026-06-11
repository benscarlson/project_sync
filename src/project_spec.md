# Project Spec: Git project syncronization


## Objective
- Write a small script that automates git pull/commit/merge/push for several repositories


## Tech Stack
- Python, using libraries and APIs as appropriate


## Project Structure
- `src/` – Application source code
- `src/tests/` – Unit and integration tests
- `docs/` – Documentation


## Boundaries
- ✅ Always: Run tests before commits, follow naming conventions
- ⚠️ Ask first: Database schema changes, adding dependencies
- 🚫 Never: Commit secrets, edit node_modules/, modify CI config

## Documentation
- Add usage documentation, with examples, in markdown format to the docs/ folder
	- Specifically include anything I need to do to configure git (assume commandline git commands work).
- Add technical documentation describing at a high level how the code works.

## Specification

Repo configuration file
* Read a list of git repos from a configuration file called "repos.json"
* Use a format for the configuration file that makes the most sense
* Put an example configuration file in the project root, called "repos_example.json"


Perform the following for each git repo

* Run git status. Depending on the status, do the following

* If there are no local updates, use git pull to download any changes that are on github. Process the next repo

* If there are local updates
* Show the status and pause the program. Ask the user if items should be added (yes/no/cancel)

* If yes
	* git add the updates

* If no
	* move to the next repo

* If cancel
	* Stop the program

* If continuing with the same repo (user responded yes)
	* Use git status to show the status of what has been added
	* Pause and ask for user input for the commit message. Provide a default commit message of "updates". Pressing enter accepts the input. Otherwise, the user can type a different commit message
	* After the user enters the commit message, commit the changes to the repo.
	* Next, do a git pull to get any changes from github.
	* Stop execution if there are any merge issues
	* If there are no merge issues, push changes to github.

* Repeat the above steps for all repos in the list

After all repos are processed

* Generate a small summary table showing what was done. Include 
	- whether there were local changes
	- whether there were changes pulled from github
	- if changes were committed or skipped

# Usage

- The code should run using the command 'project_sync'. Create a wrapper script that loads the environment and then executes project_sync.sh. I will link to this command using ~/bin so that I can execute this command from any directory.