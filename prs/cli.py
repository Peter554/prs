import asyncio

import typer

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
    )
    prs_where_my_review_has_been_requested = (
        prs_where_my_review_has_been_requested_task.result()
    )

    for pr in my_prs:
        print(pr.json())

    for pr in prs_where_my_review_has_been_requested:
        print(pr.json())


def _deduplicate_prs(*prs: list[github.PullRequest]) -> list[github.PullRequest]:
    deduplicated_prs = set([pr for prs_ in prs for pr in prs_])
    return list(sorted(deduplicated_prs, key=lambda pr: pr.updated_at, reverse=True))
