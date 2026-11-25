# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

import json
import sqlite3
from dataclasses import replace
from importlib.resources import files
from typing import TYPE_CHECKING

import pytest

from tbhbgraph.decisions import Adr, DecisionIssue
from tbhbgraph.projection import lookup_decision, upsert_decision

if TYPE_CHECKING:
    from collections.abc import Iterator


def _sql(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture
def issue() -> DecisionIssue:
    return DecisionIssue(
        repo="example-org/example-repo",
        number=81,
        node_id="I_fictional81",
        title="Choose Postgres",
        state="open",
        body="A reader's choice.\nADR: docs/adr/storage.md",
        comments=("Keep café text.", "'); DROP TABLE adrs; --"),
    )


@pytest.fixture
def record() -> Adr:
    return Adr("docs/adr/storage.md", "a" * 40, "Storage", "Use Postgres.")


@pytest.fixture
def database() -> Iterator[sqlite3.Connection]:
    schema = files("tbhbgraph").joinpath("decisions.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        yield connection
    connection.close()


def test_upsert_issue_statements(issue: DecisionIssue) -> None:
    assert upsert_decision(issue) == (
        (
            _sql(
                """INSERT INTO decision_issues
                (repository, number, node_id, title, state, body, comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (repository, number) DO UPDATE SET
                node_id = EXCLUDED.node_id, title = EXCLUDED.title,
                state = EXCLUDED.state, body = EXCLUDED.body,
                comments = EXCLUDED.comments"""
            ),
            (
                "example-org/example-repo",
                81,
                "I_fictional81",
                "Choose Postgres",
                "open",
                "A reader's choice.\nADR: docs/adr/storage.md",
                '["Keep caf\\u00e9 text.", "\'); DROP TABLE adrs; --"]',
            ),
        ),
        (
            "DELETE FROM decision_adr_links WHERE repository = %s AND number = %s",
            ("example-org/example-repo", 81),
        ),
    )


def test_upsert_adr_statements(issue: DecisionIssue, record: Adr) -> None:
    statements = upsert_decision(issue, record)
    assert statements[:2] == upsert_decision(issue)
    assert statements[2:] == (
        (
            _sql(
                """INSERT INTO adrs (repository, path, commit_sha, title, body)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (repository, path, commit_sha) DO UPDATE SET
                title = EXCLUDED.title, body = EXCLUDED.body"""
            ),
            (
                "example-org/example-repo",
                "docs/adr/storage.md",
                "a" * 40,
                "Storage",
                "Use Postgres.",
            ),
        ),
        (
            _sql(
                """INSERT INTO decision_adr_links
                (repository, number, adr_path, adr_commit)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (repository, number) DO UPDATE SET
                adr_path = EXCLUDED.adr_path, adr_commit = EXCLUDED.adr_commit"""
            ),
            ("example-org/example-repo", 81, "docs/adr/storage.md", "a" * 40),
        ),
    )


def test_lookup_statement() -> None:
    assert lookup_decision("example-org/example-repo", 81) == (
        _sql(
            """SELECT i.repository, i.number, i.node_id, i.title, i.state, i.body,
            i.comments, a.path, a.commit_sha, a.title, a.body
            FROM decision_issues AS i
            LEFT JOIN decision_adr_links AS l
            ON l.repository = i.repository AND l.number = i.number
            LEFT JOIN adrs AS a
            ON a.repository = l.repository AND a.path = l.adr_path
            AND a.commit_sha = l.adr_commit
            WHERE i.repository = %s AND i.number = %s"""
        ),
        ("example-org/example-repo", 81),
    )


@pytest.mark.parametrize(
    "replacement",
    [
        None,
        Adr("docs/adr/storage.md", "a" * 40, "Updated", "Changed."),
        Adr("docs/adr/storage.md", "b" * 40, "Revision", "New commit."),
        Adr("docs/adr/next.md", "b" * 40, "Next", "New path."),
    ],
)
def test_schema_and_replacement(
    database: sqlite3.Connection,
    issue: DecisionIssue,
    record: Adr,
    replacement: Adr | None,
) -> None:
    lookup, key = lookup_decision(issue.repo, issue.number)
    lookup = lookup.replace("%s", "?")
    assert database.execute(lookup, key).fetchone() is None
    updated = replace(
        issue,
        node_id="I_fictional82",
        title="Changed",
        state="closed",
        body="",
        comments=(),
    )
    for current_issue, current_adr in ((issue, record), (updated, replacement)):
        with database:
            for sql, parameters in upsert_decision(current_issue, current_adr):
                database.execute(sql.replace("%s", "?"), parameters)
        row = database.execute(lookup, key).fetchone()
        assert row is not None
        assert row[:6] == (
            current_issue.repo,
            current_issue.number,
            current_issue.node_id,
            current_issue.title,
            current_issue.state,
            current_issue.body,
        )
        assert json.loads(row[6]) == list(current_issue.comments)
        assert row[7:] == (
            (current_adr.path, current_adr.commit, current_adr.title, current_adr.body)
            if current_adr is not None
            else (None, None, None, None)
        )
    assert database.execute("SELECT COUNT(*) FROM decision_issues").fetchone() == (1,)
    assert database.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(
    ("repository", "number"),
    [("example-org/example-repo", 82), ("example-org/example-repo-2", 81)],
)
def test_schema_keeps_issue_keys_separate(
    database: sqlite3.Connection,
    issue: DecisionIssue,
    record: Adr,
    repository: str,
    number: int,
) -> None:
    other = replace(issue, repo=repository, number=number)
    other_adr = replace(record, commit="b" * 40, body="Another revision.")
    for current_issue, current_adr in (
        (issue, record),
        (other, other_adr),
        (issue, None),
    ):
        for sql, parameters in upsert_decision(current_issue, current_adr):
            database.execute(sql.replace("%s", "?"), parameters)
    lookup, key = lookup_decision(repository, number)
    row = database.execute(lookup.replace("%s", "?"), key).fetchone()
    assert row is not None
    assert row[:2] == (repository, number)
    assert row[7:] == (
        other_adr.path,
        other_adr.commit,
        other_adr.title,
        other_adr.body,
    )
