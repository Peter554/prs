import pydantic


class Config(pydantic.BaseModel):
    username: str
    team_aliases: dict[str, str] = pydantic.Field(default_factory=dict)
