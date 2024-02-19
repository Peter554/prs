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
prs review-requested
prs rr
prs

# PRs I am requested to review (including teams)
prs review-requested-all
prs rra

# PRs I have reviewed (updated in the last 2 weeks)
prs reviewed
prs r

# PRs a team is requested to review
prs team-review-requested:<team>
prs trr:<team>
prs trr:<team_alias>

# Add a team alias
prs add-team-alias

# Closed/merged PRs
prs <cmd> --closed
prs <cmd> -c
```