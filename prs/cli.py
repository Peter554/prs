import asyncio

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

    my_prs = _deduplicate_prs(
        prs_where_i_am_author_task.result(),
        prs_where_i_am_assigned_task.result(),
    )[:10]
    prs_where_my_review_has_been_requested = (
        prs_where_my_review_has_been_requested_task.result()
    )[:10]

    console = Console()
    if my_prs:
        _render_prs(console, "My PRs", my_prs)
    if prs_where_my_review_has_been_requested:
        _render_prs(
            console, "My review requested", prs_where_my_review_has_been_requested
        )


def _deduplicate_prs(*prs: list[github.PullRequest]) -> list[github.PullRequest]:
    deduplicated_prs = set([pr for prs_ in prs for pr in prs_])
    return list(sorted(deduplicated_prs, key=lambda pr: pr.updated_at, reverse=True))


def _render_prs(console: Console, title: str, prs: list[github.PullRequest]) -> None:
    table = Table(title=title)

    table.add_column("PR")
    table.add_column("Title", max_width=64, no_wrap=True)
    table.add_column("Created")
    table.add_column("Updated")

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
