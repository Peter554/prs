from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Literal

import pydantic


class GitHubError(Exception): ...


class PullRequest(pydantic.BaseModel):
    author: str
    number: int
    title: str
    url: str
    state: Literal["open", "closed"]
    is_draft: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    closed_at: datetime.datetime | None
    merged_at: datetime.datetime | None
    commit_status: Literal["unknown", "pending", "success", "failure"]
    review_status: Literal["unknown", "approved"]

    @pydantic.computed_field  # type:ignore
    @property
    def owner(self) -> str:
        return self.url.split("/")[-4]

    @pydantic.computed_field  # type:ignore
    @property
    def repo(self) -> str:
        return self.url.split("/")[-3]

    @classmethod
    def from_search_api_response(
        cls,
        response: dict[str, Any],
    ) -> PullRequest:
        return cls(
            author=response["user"]["login"],
            number=response["number"],
            title=response["title"],
            url=response["html_url"],
            state=response["state"],
            is_draft=response["draft"],
            created_at=response["created_at"],
            updated_at=response["updated_at"],
            closed_at=response["closed_at"],
            merged_at=response["pull_request"]["merged_at"],
            commit_status="unknown",
            review_status="unknown",
        )


class PullRequestsClient:
    def __init__(self, base_query: str):
        self._base_query = base_query

    async def get_pull_requests(self, n: int, *queries: str) -> list[PullRequest]:
        """
        Get a list of pull requests from GitHub.
        Accept multiple queries here, since GitHub search syntax
        does not support an OR operation.
        """

        if n > 100:
            raise ValueError("n must be <= 100")

        pr_tasks: list[asyncio.Task[list[PullRequest]]] = []
        try:
            async with asyncio.TaskGroup() as tg:
                for query in queries:
                    pr_tasks.append(tg.create_task(self._get_pull_requests(query)))
        except* GitHubError as e:
            raise e.exceptions[0]

        prs: dict[str, PullRequest] = {}
        for pr_task in pr_tasks:
            prs |= {pr.url: pr for pr in pr_task.result()}

        return list(sorted(prs.values(), key=lambda pr: pr.created_at, reverse=True))[
            :n
        ]

    async def _get_pull_requests(self, query: str) -> list[PullRequest]:
        query = self._base_query + " " + query

        try:
            async with asyncio.TaskGroup() as tg:
                base_task = tg.create_task(self._get_raw_pull_requests(query))
                # Additionally query pending/success/failure/approved PRs, since the
                # response does not include this information. This workaround can
                # quite quickly lead to hitting rate limits,
                # so don't stack too many calls here.
                pending_task = tg.create_task(
                    self._get_raw_pull_requests(query + " status:pending")
                )
                success_task = tg.create_task(
                    self._get_raw_pull_requests(query + " status:success")
                )
                failure_task = tg.create_task(
                    self._get_raw_pull_requests(query + " status:failure")
                )
                approved_task = tg.create_task(
                    self._get_raw_pull_requests(query + " review:approved")
                )
        except* GitHubError as e:
            raise e.exceptions[0]

        prs = [PullRequest.from_search_api_response(pr) for pr in base_task.result()]

        pending_pr_urls = set(pr["html_url"] for pr in pending_task.result())
        success_pr_urls = set(pr["html_url"] for pr in success_task.result())
        failure_pr_urls = set(pr["html_url"] for pr in failure_task.result())
        approved_pr_urls = set(pr["html_url"] for pr in approved_task.result())

        for pr in prs:
            if pr.url in success_pr_urls:
                pr.commit_status = "success"
            elif pr.url in failure_pr_urls:
                pr.commit_status = "failure"
            elif pr.url in pending_pr_urls:
                pr.commit_status = "pending"

            if pr.url in approved_pr_urls:
                pr.review_status = "approved"

        return prs

    async def _get_raw_pull_requests(self, query: str) -> Any:
        process = await asyncio.create_subprocess_exec(
            *[
                "gh",
                "api",
                "-X",
                "GET",
                "/search/issues?per_page=100",
                "-f",
                f"q=is:pr sort:created-desc {query}",
            ],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stderr != b"":
            raise GitHubError(stderr.decode())

        return json.loads(stdout.strip())["items"]
