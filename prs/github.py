from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Literal

import pydantic


class GitHubError(Exception): ...


class PullRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

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

    def __hash__(self) -> int:
        return hash(self.url)

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


async def get_pull_requests(query: str) -> list[PullRequest]:
    try:
        async with asyncio.TaskGroup() as tg:
            base_task = tg.create_task(_get_pull_requests(query))
            pending_task = tg.create_task(_get_pull_requests(query + " status:pending"))
            success_task = tg.create_task(_get_pull_requests(query + " status:success"))
            failure_task = tg.create_task(_get_pull_requests(query + " status:failure"))
            approved_task = tg.create_task(
                _get_pull_requests(query + " review:approved")
            )
    except* GitHubError as e:
        raise e.exceptions[0]

    pending = set(pr["html_url"] for pr in pending_task.result())
    success = set(pr["html_url"] for pr in success_task.result())
    failure = set(pr["html_url"] for pr in failure_task.result())
    approved = set(pr["html_url"] for pr in approved_task.result())

    prs = [PullRequest.from_search_api_response(pr) for pr in base_task.result()]

    for pr in prs:
        if pr.url in success:
            pr.commit_status = "success"
        elif pr.url in failure:
            pr.commit_status = "failure"
        elif pr.url in pending:
            pr.commit_status = "pending"

        if pr.url in approved:
            pr.review_status = "approved"

    return prs


async def _get_pull_requests(query: str) -> Any:
    process = await asyncio.create_subprocess_exec(
        *[
            "gh",
            "api",
            "-X",
            "GET",
            "/search/issues?per_page=50",
            "-f",
            f"q=is:pr archived:false sort:created-desc is:open {query}",
        ],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if stderr != b"":
        raise GitHubError(stderr.decode())

    return json.loads(stdout.strip())["items"]
