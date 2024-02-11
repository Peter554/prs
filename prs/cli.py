import asyncio
import datetime

import humanize
import typer
from rich.console import Console
from rich.table import Table

from . import github

cli = typer.Typer()


@cli.command()
def main() -> None:
    asyncio.run(main_async())


async def main_async() -> None:
    two_weeks_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=2)

    async with asyncio.TaskGroup() as tg:
        prs_where_i_am_author_task = tg.create_task(
            github.get_pull_requests("author:peter554")
        )
        prs_where_i_am_assigned_task = tg.create_task(
            github.get_pull_requests("assignee:peter554")
        )
        prs_where_my_review_has_been_requested_task = tg.create_task(
            github.get_pull_requests("user-review-requested:peter554")
        )
        prs_i_have_reviewed_task = tg.create_task(
            github.get_pull_requests(
                f"reviewed-by:peter554 updated:>{two_weeks_ago.date()}"
            )
        )

    my_prs = set(prs_where_i_am_author_task.result()) | set(
        prs_where_i_am_assigned_task.result()
    )
    prs_where_my_review_has_been_requested = set(
        prs_where_my_review_has_been_requested_task.result()
    )
    prs_i_have_reviewed = set(prs_i_have_reviewed_task.result()) - my_prs

    console = Console()
    _render_prs(
        console,
        "My PRs",
        _sort_and_take(my_prs, 10),
    )
    _render_prs(
        console,
        "PRs where my review is requested",
        _sort_and_take(prs_where_my_review_has_been_requested, 10),
    )
    _render_prs(
        console,
        "PRs I have reviewed",
        _sort_and_take(prs_i_have_reviewed, 10),
    )


def _sort_and_take(prs: set[github.PullRequest], n: int) -> list[github.PullRequest]:
    return list(sorted(prs, key=lambda pr: pr.updated_at, reverse=True))[:n]


def _render_prs(console: Console, title: str, prs: list[github.PullRequest]) -> None:
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
