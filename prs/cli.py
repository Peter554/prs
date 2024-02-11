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
    mode: Annotated[str, typer.Argument()] = "review-requests", n: int = 10
) -> None:
    asyncio.run(amain(mode, n))


async def amain(mode: str, n: int) -> None:
    try:
        config_ = config.read_config()
    except config.ConfigNotFound:
        print(f"No config file found ({config.config_path()}), creating one now...")
        username = typer.prompt("Username")
        config_ = config.Config(username=username)
        config.write_config(config_)
        return await amain(mode, n)

    if mode == "view-config":
        print(str(config.config_path()))
        pprint(config_.model_dump())
        return

    if mode == "add-team-alias":
        alias = typer.prompt("Alias")
        team = typer.prompt("Team")
        config_.team_aliases[alias] = team
        config.write_config(config_)
        return

    async with asyncio.TaskGroup() as tg_:
        tg = PullRequestsTaskGroup(tg_)
        if mode in ("mine", "m"):
            title = "My PRs"
            tg.include(f"author:{config_.username}")
            tg.include(f"assignee:{config_.username}")
        elif mode in ("review-requests", "rr"):
            title = "PRs where my review is requested"
            tg.include(f"user-review-requested:{config_.username}")
        elif mode in ("reviewed", "r"):
            title = "PRs I have reviewed (updated in last 2 weeks)"
            two_weeks_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
                weeks=2
            )
            tg.include(
                f"reviewed-by:{config_.username} updated:>{two_weeks_ago.date()} "
                f"-author:{config_.username} -assignee:{config_.username}"
            )
        elif mode.startswith("team:") or mode.startswith("t:"):
            team = mode.removeprefix("team:")
            team = team.removeprefix("t:")
            if team in config_.team_aliases:
                team = config_.team_aliases[team]
            title = f"PRs where review is requested  (team {team})"
            tg.include(
                f"team-review-requested:{team} "
                f"-author:{config_.username} -assignee:{config_.username}"
            )
        else:
            ValueError(f'mode "{mode}" not supported')

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
    table.add_column("Author")
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
            humanize.naturaltime(pr.created_at),
            humanize.naturaltime(pr.updated_at),
            {
                "success": "🟢",
                "failure": "🔴",
                "pending": "🟡",
                "unknown": "⚪",
            }[pr.commit_status]
            + ("🚢" if pr.approved else ""),
        )

    console.print(table)
