# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from dataclasses import replace

import pytest

from tbhbgraph.decisions import Adr, DecisionIndex, DecisionIssue, adr_link


@pytest.fixture
def linked_issue() -> DecisionIssue:
    return DecisionIssue(
        repo="example-org/example-repo",
        number=42,
        node_id="I_fictional42",
        title="Choose a search index",
        state="open",
        body="Search supports decisions.\nADR: docs/adr/0001-example.md",
        comments=("SEARCH helps readers.", "Prefer simple storage."),
    )


@pytest.fixture
def unlinked_issue() -> DecisionIssue:
    return DecisionIssue(
        repo="example-org/example-repo",
        number=17,
        node_id="I_fictional17",
        title="Choose storage",
        state="closed",
        body="Keep the index in memory.",
        comments=("Search can follow later.",),
    )


@pytest.fixture
def adr() -> Adr:
    return Adr(
        path="docs/adr/0001-example.md",
        commit="0123456789abcdef0123456789abcdef01234567",
        title="Use a simple index",
        body="Search search: retrieve decisions with café_2026 tokens.",
    )


def test_show_with_adr(linked_issue: DecisionIssue, adr: Adr) -> None:
    index = DecisionIndex()
    index.put(linked_issue, adr)
    assert index.show(linked_issue.repo, linked_issue.number) == (linked_issue, adr)
    assert adr.path == adr_link(linked_issue)
    assert adr.commit == "0123456789abcdef0123456789abcdef01234567"
    assert adr.title == "Use a simple index"
    assert linked_issue.node_id == "I_fictional42"
    assert linked_issue.state == "open"


def test_show_without_adr(linked_issue: DecisionIssue) -> None:
    index = DecisionIndex()
    index.put(linked_issue)
    assert index.show(linked_issue.repo, linked_issue.number) == (linked_issue, None)


def test_show_missing() -> None:
    assert DecisionIndex().show("example-org/example-repo", 99) is None


def test_put_replaces_issue_and_adr(linked_issue: DecisionIssue, adr: Adr) -> None:
    index = DecisionIndex()
    index.put(linked_issue, adr)
    updated = replace(linked_issue, title="Updated", body="Changed", comments=())
    index.put(updated)
    assert index.show(updated.repo, updated.number) == (updated, None)
    assert index.search("search") == []
    assert index.search("updated") == [updated]


def test_search_ranking(
    linked_issue: DecisionIssue, unlinked_issue: DecisionIssue, adr: Adr
) -> None:
    index = DecisionIndex()
    index.put(unlinked_issue)
    index.put(linked_issue, adr)
    assert index.search("SeArCh!") == [linked_issue, unlinked_issue]
    # Different query terms change the order by total match count.
    assert index.search("memory index storage") == [
        unlinked_issue,
        linked_issue,
    ]


def test_search_ties_use_repo_then_number(unlinked_issue: DecisionIssue) -> None:
    index = DecisionIndex()
    higher_number = replace(unlinked_issue, number=21, node_id="I_fictional21")
    other_repo = replace(unlinked_issue, repo="example-org/example-repo-2", number=1)
    for issue in (other_repo, higher_number, unlinked_issue):
        index.put(issue)
    assert index.show(other_repo.repo, other_repo.number) == (other_repo, None)
    assert index.search("search") == [unlinked_issue, higher_number, other_repo]


@pytest.mark.parametrize("query", ["missing", "searching", "", "!!!"])
def test_search_no_matches(unlinked_issue: DecisionIssue, query: str) -> None:
    index = DecisionIndex()
    index.put(unlinked_issue)
    assert index.search(query) == []


@pytest.mark.parametrize("query", ["retrieve", "CAFÉ", "2026", "café-2026"])
def test_search_adr_body(linked_issue: DecisionIssue, adr: Adr, query: str) -> None:
    index = DecisionIndex()
    index.put(linked_issue, adr)
    assert index.search(query) == [linked_issue]


def test_adr_link(linked_issue: DecisionIssue) -> None:
    assert adr_link(linked_issue) == "docs/adr/0001-example.md"


def test_adr_link_without_line(unlinked_issue: DecisionIssue) -> None:
    assert adr_link(unlinked_issue) is None


def test_adr_link_first_line_wins(linked_issue: DecisionIssue) -> None:
    issue = replace(
        linked_issue, body=linked_issue.body + "\nADR: docs/adr/0002-next.md"
    )
    assert adr_link(issue) == "docs/adr/0001-example.md"


@pytest.mark.parametrize(
    "body", ["adr: docs/adr/example.md", " ADR: docs/adr/example.md"]
)
def test_adr_link_requires_exact_prefix(linked_issue: DecisionIssue, body: str) -> None:
    assert adr_link(replace(linked_issue, body=body)) is None
