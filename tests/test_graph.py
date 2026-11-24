# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from importlib.metadata import version
from typing import TYPE_CHECKING

from tbhbgraph import TOOLS, config

if TYPE_CHECKING:
    import pytest


def test_graph_version(capsys: pytest.CaptureFixture[str]) -> None:
    graph = TOOLS["graph"]
    prog = "tbhbdev graph"

    assert graph(["--version"], prog) == 0
    assert capsys.readouterr().out == f"{prog}, version {version('tbhbgraph')}\n"

    assert graph([], prog) == 0
    assert capsys.readouterr().out == ""

    assert graph(["--unknown"], prog) == 2
    error = capsys.readouterr().err
    assert f"Usage: {prog} " in error
    assert "--unknown" in error
    assert config("settings.toml") is None
