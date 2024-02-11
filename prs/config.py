import pathlib

import pydantic
import typer


class ConfigNotFound(Exception): ...


class Config(pydantic.BaseModel):
    username: str
    team_aliases: dict[str, str] = pydantic.Field(default_factory=dict)


def config_path() -> pathlib.Path:
    app_dir = typer.get_app_dir("prs")
    return pathlib.Path(app_dir) / "config.json"


def read_config() -> Config:
    config_path_ = config_path()
    if not config_path_.is_file():
        raise ConfigNotFound

    with open(config_path_) as f:
        return Config.model_validate_json(f.read())


def write_config(config: Config) -> None:
    config_path_ = config_path()
    config_path_.parent.mkdir(exist_ok=True, parents=True)
    with open(config_path_, "w") as f:
        f.write(config.model_dump_json())
