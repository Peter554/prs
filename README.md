# prs

CLI to list GitHub PRs

* Clone the repo
* `pipx install ./path/to/repo`
* Create the config file (e.g. username, team aliases)

```bash
# PRs I have created or am assigned to
prs mine
prs m

# PRs I am requested to review
prs review-requests
prs rr
prs

# PRs I have reviewed (updated in the last 2 weeks)
prs reviewed
prs r

# PRs a team is requested to review
prs team:<team>
prs t:<team>
prs t:<team_alias>
```