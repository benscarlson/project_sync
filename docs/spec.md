The name of the main command should be `reposync`

## reposync update

`reposync` or `reposync update` should run the main process that commits, pulls, and pushes each repo

After writing the final table print the date use format 'Name of day, Month Name, Day Number, YYYY, Hour:Minute'. Example: Tuesday, October 6, 2026 17:00

Process the repos alphabetically, according to owner/reponame. e.g. 

benscarlson/aaa
benscarlson/bbb
ycrc/aaa
ycrc/bbb

The table should have the owner prefixed. e.g. benscarlson/llm instead of llm

The table summary should also output in alphabetical order.

## reposync add

`reposync add reponame` will add reponame to repos.json

Insert into repos.json in alphabetical order according to owner/reponame


## reosync list

`reposync list` lists all repos. Print a table with the github repo name (e.g. benscarlson/myrepo) and the full path to the repo (e.g. ~/projects/myrepo). Print in alphabetical order.

## reposync remove

`reposync remove reponame` removes reponame from repos.json