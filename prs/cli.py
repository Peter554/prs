import asyncio
import datetime
from typing import Annotated

import humanize
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import github

cli = typer.Typer()
console = Console()


@cli.command()
def main(
    mode: Annotated[str, typer.Argument()] = "review-requests", n: int = 10
) -> None:
    asyncio.run(amain(mode, n))


async def amain(mode: str, n: int) -> None:
    async with asyncio.TaskGroup() as tg_:
        tg = PullRequestsTaskGroup(tg_)
        if mode in ("mine", "m"):
            title = "My PRs"
            tg.include("author:peter554")
            tg.include("assignee:peter554")
        elif mode in ("review-requests", "rr"):
            title = "PRs where my review is requested"
            tg.include("user-review-requested:peter554")
        elif mode in ("reviewed", "r"):
            title = "PRs I have reviewed (updated in last 2 weeks)"
            two_weeks_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
                weeks=2
            )
            tg.include(f"reviewed-by:peter554 updated:>{two_weeks_ago.date()}")
            tg.exclude("author:peter554")
            tg.exclude("assignee:peter554")
        else:
            ValueError(f'mode "{mode}" not supported')

    _render_prs(title, tg.result()[:n])


class PullRequestsTaskGroup:
    def __init__(self, tg: asyncio.TaskGroup) -> None:
        self._tg = tg
        self._include: list[asyncio.Task[list[github.PullRequest]]] = []
        self._exclude: list[asyncio.Task[list[github.PullRequest]]] = []

    def include(self, query: str) -> None:
        self._include.append(self._tg.create_task(github.get_pull_requests(query)))

    def exclude(self, query: str) -> None:
        self._exclude.append(self._tg.create_task(github.get_pull_requests(query)))

    def result(self) -> list[github.PullRequest]:
        prs: set[github.PullRequest] = set()
        for include in self._include:
            prs |= set(include.result())
        for exclude in self._exclude:
            prs -= set(exclude.result())
        return list(sorted(prs, key=lambda pr: pr.updated_at, reverse=True))


def _render_prs(title: str, prs: list[github.PullRequest]) -> None:
    table = Table(title=title, expand=True)

    table.add_column("PR")
    table.add_column("Title", max_width=64, no_wrap=True)
    table.add_column("Author")
    table.add_column("Updated")
    table.add_column("Created")

    for pr in prs:
        if pr.is_draft:
            color = "grey"
        else:
            color = "green"
        table.add_row(
            f"[link={pr.url}][{color}]{pr.repo}/{pr.number}[/][/]",
            f"[link={pr.url}]{escape(pr.title)}[/]",
            pr.author,
            humanize.naturaltime(pr.updated_at),
            humanize.naturaltime(pr.created_at),
        )

    console.print(table)
