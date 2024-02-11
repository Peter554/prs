# prs

CLI to list GitHub PRs.

Pre-requisites:

* Install and set up the [GitHub CLI](https://cli.github.com/)
* Install [pipx](https://pipx.pypa.io/stable/)
* Python 3.11 installed (e.g. with [pyenv](https://github.com/pyenv/pyenv)) 

Install:

* Clone the repo
* `pipx install ./path/to/repo`

```bash
# PRs I have created or am assigned to
prs mine
prs m

# PRs I am requested to review (excluding teams)
prs review-requests
prs rr
prs

# PRs I am requested to review (including teams)
prs review-requests-teams
prs rrt

# PRs I have reviewed (updated in the last 2 weeks)
prs reviewed
prs r

# PRs a team is requested to review
prs team:<team>
prs t:<team>
prs t:<team_alias>

# Add a team alias
prs add-team-alias
```