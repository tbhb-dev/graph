# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""Pure Postgres statements for Decision issues and their current ADR links."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tbhbgraph.decisions import Adr, DecisionIssue

type Statement = tuple[str, tuple[str | int, ...]]


def upsert_decision(
    issue: DecisionIssue, adr: Adr | None = None
) -> tuple[Statement, ...]:
    """Return ordered statements to execute together in one transaction.

    Comments use JSON text. ADR snapshots remain after their links change.
    """
    statements: tuple[Statement, ...] = (
        (
            (
                "INSERT INTO decision_issues "
                "(repository, number, node_id, title, state, body, comments) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (repository, number) DO UPDATE SET "
                "node_id = EXCLUDED.node_id, title = EXCLUDED.title, "
                "state = EXCLUDED.state, body = EXCLUDED.body, "
                "comments = EXCLUDED.comments"
            ),
            (
                issue.repo,
                issue.number,
                issue.node_id,
                issue.title,
                issue.state,
                issue.body,
                json.dumps(issue.comments),
            ),
        ),
        (
            "DELETE FROM decision_adr_links WHERE repository = %s AND number = %s",
            (issue.repo, issue.number),
        ),
    )
    if adr is None:
        return statements
    return (
        *statements,
        (
            (
                "INSERT INTO adrs (repository, path, commit_sha, title, body) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (repository, path, commit_sha) DO UPDATE SET "
                "title = EXCLUDED.title, body = EXCLUDED.body"
            ),
            (issue.repo, adr.path, adr.commit, adr.title, adr.body),
        ),
        (
            (
                "INSERT INTO decision_adr_links "
                "(repository, number, adr_path, adr_commit) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (repository, number) DO UPDATE SET "
                "adr_path = EXCLUDED.adr_path, adr_commit = EXCLUDED.adr_commit"
            ),
            (issue.repo, issue.number, adr.path, adr.commit),
        ),
    )


def lookup_decision(repository: str, number: int) -> Statement:
    """Read an issue and its optional ADR using only the Postgres projection."""
    return (
        (
            "SELECT i.repository, i.number, i.node_id, i.title, i.state, i.body, "
            "i.comments, a.path, a.commit_sha, a.title, a.body "
            "FROM decision_issues AS i "
            "LEFT JOIN decision_adr_links AS l "
            "ON l.repository = i.repository AND l.number = i.number "
            "LEFT JOIN adrs AS a "
            "ON a.repository = l.repository AND a.path = l.adr_path "
            "AND a.commit_sha = l.adr_commit "
            "WHERE i.repository = %s AND i.number = %s"
        ),
        (repository, number),
    )
