import asyncio
import datetime
from typing import Annotated

import humanize
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import config, github

cli = typer.Typer()

console = Console()
stderr_console = Console(stderr=True)


@cli.command()
def main(
    cmd: Annotated[str, typer.Argument()] = "review-requested",
    n: int = 10,
    closed: Annotated[bool, typer.Option("--closed", "-c")] = False,
) -> None:
    asyncio.run(amain(cmd, n, closed))


async def amain(cmd: str, n: int, closed: bool) -> None:
    try:
        config_ = config.read_config()
    except config.ConfigNotFound:
        stderr_console.print(
            f"No config file found ({config.config_path()}), creating one now..."
        )
        username = typer.prompt("Username")
        config_ = config.Config(username=username)
        config.write_config(config_)

    if cmd == "view-config":
        console.print(str(config.config_path()))
        console.print(config_.model_dump())
        return

    if cmd == "add-team-alias":
        alias = typer.prompt("Alias")
        team = typer.prompt("Team")
        config_.team_aliases[alias] = team
        config.write_config(config_)
        return

    two_weeks_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=2)

    try:
        if closed:
            prs_client = github.PullRequestsClient(
                f"archived:false is:closed closed:>{two_weeks_ago.date()}"
            )
        else:
            prs_client = github.PullRequestsClient("archived:false is:open")

        if cmd in ("mine", "m"):
            title = "My PRs"
            prs = await prs_client.get_pull_requests(
                n,
                f"author:{config_.username}",
                f"assignee:{config_.username}",
            )
        elif cmd in ("review-requested", "rr"):
            title = "PRs where my review is requested"
            prs = await prs_client.get_pull_requests(
                n, f"user-review-requested:{config_.username}"
            )
        elif cmd in ("review-requested-all", "rra"):
            title = "PRs where my review is requested (including teams)"
            prs = await prs_client.get_pull_requests(
                n, f"review-requested:{config_.username}"
            )
        elif cmd in ("reviewed", "r"):
            title = "PRs I have reviewed (updated in last 2 weeks)"
            prs = await prs_client.get_pull_requests(
                n,
                f"reviewed-by:{config_.username} updated:>{two_weeks_ago.date()} "
                f"-author:{config_.username} -assignee:{config_.username}",
            )
        elif cmd.startswith("team-review-requested:") or cmd.startswith("trr:"):
            team = cmd.removeprefix("team-review-requested:")
            team = team.removeprefix("trr:")
            if team in config_.team_aliases:
                team = config_.team_aliases[team]
            title = f"PRs where review is requested (team {team})"
            prs = await prs_client.get_pull_requests(
                n,
                f"team-review-requested:{team} "
                f"-author:{config_.username} -assignee:{config_.username}",
            )
        else:
            raise ValueError(f'Command "{cmd}" not supported')
    except github.GitHubError:
        stderr_console.print_exception()
        return

    render_prs(title, prs)


def render_prs(title: str, prs: list[github.PullRequest]) -> None:
    table = Table(title=title, expand=True)

    table.add_column("PR")
    table.add_column("Title", max_width=64, no_wrap=True)
    table.add_column("Author", max_width=16, no_wrap=True)
    table.add_column("Created")
    table.add_column("Updated")
    table.add_column("Status")

    for pr in prs:
        if pr.merged_at is not None:
            color = "purple"
        elif pr.closed_at is not None:
            color = "red"
        elif pr.is_draft:
            color = "grey"
        else:
            color = "green"
        table.add_row(
            f"[link={pr.url}][{color}]{pr.repo}/{pr.number}[/][/]",
            f"[link={pr.url}]{escape(pr.title)}[/]",
            pr.author,
            humanize.naturaltime(pr.created_at).removesuffix(" ago"),
            humanize.naturaltime(pr.updated_at).removesuffix(" ago"),
            {
                "success": "🟢",
                "failure": "🔴",
                "pending": "🟡",
                "unknown": "⚪",
            }[pr.commit_status]
            + ("🚢" if pr.review_status == "approved" else ""),
        )

    console.print(table)
