from __future__ import annotations

import asyncio
import datetime
import json
from typing import Any, Literal

import pydantic


class PullRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    number: int
    title: str
    url: str
    state: Literal["open", "closed"]
    is_draft: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def __hash__(self) -> int:
        return hash((self.owner, self.repo, self.number))

    @pydantic.computed_field  # type:ignore
    @property
    def owner(self) -> str:
        return self.url.split("/")[-4]

    @pydantic.computed_field  # type:ignore
    @property
    def repo(self) -> str:
        return self.url.split("/")[-3]

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> PullRequest:
        return cls(
            number=response["number"],
            title=response["title"],
            url=response["html_url"],
            state=response["state"],
            is_draft=response["draft"],
            created_at=response["created_at"],
            updated_at=response["updated_at"],
        )


async def get_pull_requests(query: str) -> list[PullRequest]:
    process = await asyncio.create_subprocess_exec(
        *[
            "gh",
            "api",
            "-X",
            "GET",
            "/search/issues",
            "-f",
            f"q=is:pr archived:false sort:updated-desc is:open {query}",
        ],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    assert stderr == b""

    return [
        PullRequest.from_api_response(response)
        for response in json.loads(stdout.strip())["items"]
    ]
