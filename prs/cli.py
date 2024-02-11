import asyncio
import datetime

import humanize
import typer
from rich.console import Console
from rich.table import Table

from . import github

cli = typer.Typer()
console = Console()


@cli.command()
def main(
    mine: bool = True, review_requests: bool = True, reviewed: bool = False
) -> None:
    asyncio.run(main_async(mine, review_requests, reviewed))


async def main_async(mine: bool, review_requests: bool, reviewed: bool) -> None:
    two_weeks_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=2)

    tasks: dict[str, asyncio.Task[list[github.PullRequest]]] = {}
    async with asyncio.TaskGroup() as tg:
        if mine:
            tasks["prs_where_i_am_author_task"] = tg.create_task(
                github.get_pull_requests("author:peter554")
            )
            tasks["prs_where_i_am_assigned_task"] = tg.create_task(
                github.get_pull_requests("assignee:peter554")
            )
        if review_requests:
            tasks["prs_where_my_review_has_been_requested_task"] = tg.create_task(
                github.get_pull_requests("user-review-requested:peter554")
            )
        if reviewed:
            tasks["prs_i_have_reviewed_task"] = tg.create_task(
                github.get_pull_requests(
                    f"reviewed-by:peter554 updated:>{two_weeks_ago.date()}"
                )
            )

    if mine:
        my_prs = set(tasks["prs_where_i_am_author_task"].result()) | set(
            tasks["prs_where_i_am_assigned_task"].result()
        )
        _render_prs(
            "My PRs",
            _sort_and_take(my_prs, 10),
        )

    if review_requests:
        prs_where_my_review_has_been_requested = set(
            tasks["prs_where_my_review_has_been_requested_task"].result()
        )
        _render_prs(
            "PRs where my review is requested",
            _sort_and_take(prs_where_my_review_has_been_requested, 10),
        )

    if reviewed:
        prs_i_have_reviewed = set(tasks["prs_i_have_reviewed_task"].result())
        if mine:
            prs_i_have_reviewed -= my_prs
        _render_prs(
            "PRs I have reviewed",
            _sort_and_take(prs_i_have_reviewed, 10),
        )


def _sort_and_take(prs: set[github.PullRequest], n: int) -> list[github.PullRequest]:
    return list(sorted(prs, key=lambda pr: pr.updated_at, reverse=True))[:n]


def _render_prs(title: str, prs: list[github.PullRequest]) -> None:
    table = Table(title=title, expand=True)

    table.add_column("PR")
    table.add_column("Title", max_width=64, no_wrap=True)
    table.add_column("Created")
    table.add_column("Updated")

    if not prs:
        table.add_row(*["-"] * 4)

    for pr in prs:
        if pr.is_draft:
            pr_key = f"[link={pr.url}][grey]{pr.repo}/{pr.number}[/][/]"
        else:
            pr_key = f"[link={pr.url}][green]{pr.repo}/{pr.number}[/][/]"
        table.add_row(
            pr_key,
            f"[link={pr.url}]{pr.title}[/]",
            humanize.naturaltime(pr.created_at),
            humanize.naturaltime(pr.updated_at),
        )

    console.print(table)
