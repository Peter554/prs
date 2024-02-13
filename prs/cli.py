import asyncio
import datetime
from typing import Annotated

import humanize
import typer
from rich.console import Console
from rich.markup import escape
from rich.pretty import pprint
from rich.table import Table

from . import config, github

cli = typer.Typer()
console = Console()


@cli.command()
def main(
    cmd: Annotated[str, typer.Argument()] = "review-requests", n: int = 10
) -> None:
    asyncio.run(amain(cmd, n))


async def amain(cmd: str, n: int) -> None:
    try:
        config_ = config.read_config()
    except config.ConfigNotFound:
        print(f"No config file found ({config.config_path()}), creating one now...")
        username = typer.prompt("Username")
        config_ = config.Config(username=username)
        config.write_config(config_)
        return await amain(cmd, n)

    if cmd == "view-config":
        print(str(config.config_path()))
        pprint(config_.model_dump())
        return

    if cmd == "add-team-alias":
        alias = typer.prompt("Alias")
        team = typer.prompt("Team")
        config_.team_aliases[alias] = team
        config.write_config(config_)
        return

    try:
        async with asyncio.TaskGroup() as tg_:
            tg = PullRequestsTaskGroup(tg_)
            if cmd in ("mine", "m"):
                title = "My PRs"
                tg.include(f"author:{config_.username}")
                tg.include(f"assignee:{config_.username}")
            elif cmd in ("review-requests", "rr"):
                title = "PRs where my review is requested"
                tg.include(f"user-review-requested:{config_.username}")
            elif cmd in ("review-requests-teams", "rrt"):
                title = "PRs where my review is requested (including teams)"
                tg.include(f"review-requested:{config_.username} ")
            elif cmd in ("reviewed", "r"):
                title = "PRs I have reviewed (updated in last 2 weeks)"
                two_weeks_ago = datetime.datetime.now(
                    datetime.UTC
                ) - datetime.timedelta(weeks=2)
                tg.include(
                    f"reviewed-by:{config_.username} updated:>{two_weeks_ago.date()} "
                    f"-author:{config_.username} -assignee:{config_.username}"
                )
            elif cmd.startswith("team:") or cmd.startswith("t:"):
                team = cmd.removeprefix("team:")
                team = team.removeprefix("t:")
                if team in config_.team_aliases:
                    team = config_.team_aliases[team]
                title = f"PRs where review is requested (team {team})"
                tg.include(
                    f"team-review-requested:{team} "
                    f"-author:{config_.username} -assignee:{config_.username}"
                )
            else:
                ValueError(f'Command "{cmd}" not supported')
    except* github.GitHubError as e:
        pprint(e.exceptions[0])
    else:
        render_prs(title, tg.result()[:n])


class PullRequestsTaskGroup:
    def __init__(self, tg: asyncio.TaskGroup) -> None:
        self._tg = tg
        self._include: list[asyncio.Task[list[github.PullRequest]]] = []

    def include(self, query: str) -> None:
        self._include.append(self._tg.create_task(github.get_pull_requests(query)))

    def result(self) -> list[github.PullRequest]:
        prs: set[github.PullRequest] = set()
        for include in self._include:
            prs |= set(include.result())
        return list(sorted(prs, key=lambda pr: pr.created_at, reverse=True))


def render_prs(title: str, prs: list[github.PullRequest]) -> None:
    table = Table(title=title, expand=True)

    table.add_column("PR")
    table.add_column("Title", max_width=64, no_wrap=True)
    table.add_column("Author", max_width=16, no_wrap=True)
    table.add_column("Created")
    table.add_column("Updated")
    table.add_column("Status")

    for pr in prs:
        if pr.is_draft:
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
            + ("🚢" if pr.approved else ""),
        )

    console.print(table)
