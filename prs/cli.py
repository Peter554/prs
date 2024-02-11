import typer

cli = typer.Typer()


@cli.command()
def main(name: str) -> None:
    print(f"Hello {name}")
