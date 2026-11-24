# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""Register the graph command as a tbhbdev plugin."""

import click


@click.group(invoke_without_command=True)
@click.version_option(package_name="tbhbgraph")
def graph() -> int:
    return 0


def main(args: list[str], prog: str) -> int:
    try:
        exit_code: int = graph.main(
            args=args,
            prog_name=prog,
            standalone_mode=False,  # pragma: no mutate - Click treats None as False.
        )
    except click.ClickException as error:
        error.show()
        return error.exit_code
    return exit_code


TOOLS = {"graph": main}


def config(name: str) -> None:  # noqa: V107 - plugin API names the argument.
    """Return None because the plugin supplies no configuration files."""
