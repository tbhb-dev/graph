# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""Decision issues, ADRs, and an in-memory search projection."""

import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionIssue:
    repo: str
    number: int
    node_id: str
    title: str
    state: str
    body: str
    comments: tuple[str, ...]


@dataclass(frozen=True)
class Adr:
    path: str
    commit: str
    title: str
    body: str


def adr_link(issue: DecisionIssue) -> str | None:
    for line in issue.body.splitlines():
        if line.startswith("ADR: "):
            return line.removeprefix("ADR: ")
    return None


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text.lower())


class DecisionIndex:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, int], tuple[DecisionIssue, Adr | None]] = {}

    def put(self, issue: DecisionIssue, adr: Adr | None = None) -> None:
        self._entries[issue.repo, issue.number] = (issue, adr)

    def show(self, repo: str, number: int) -> tuple[DecisionIssue, Adr | None] | None:
        return self._entries.get((repo, number))

    def search(self, text: str) -> list[DecisionIssue]:
        query = _words(text)
        ranked: list[tuple[int, DecisionIssue]] = []
        for issue, adr in self._entries.values():
            content = " ".join((issue.title, issue.body, *issue.comments))
            if adr is not None:
                content += " " + adr.body
            counts = Counter(_words(content))
            score = sum(counts[word] for word in query)
            if score > 0:
                ranked.append((score, issue))
        ranked.sort(key=lambda item: (-item[0], item[1].repo, item[1].number))
        return [issue for _, issue in ranked]
