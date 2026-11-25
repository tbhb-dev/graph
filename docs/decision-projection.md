# Decision projection

Decision bodies link to an architecture decision record (ADR) with a line of the form `ADR: <repo-relative path>`. The prefix is case-sensitive and starts in column one. The first matching line wins. This preserves the existing `adr_link` behavior and lets authors link a document without extra issue metadata.

The convention uses plain text rather than a Markdown link or a structured issue field. Markdown links would need rules to distinguish ADRs from other documents. A structured field would need a workflow change. Guessing paths from titles would make links depend on naming choices.

TECH-DEBT: The link format is the team's convention until the Decision workflow specifies one.

## Storage and execution

`decisions.sql` creates plain Postgres tables. Issue keys contain the repository and number. Comments occupy one column as JSON text, preserving their order. ADR keys contain the repository, relative path, and commit. Each issue has at most one link, which selects an exact ADR revision.

`upsert_decision` returns SQL text and bound parameter tuples. The caller executes the returned statements in order within one transaction. An upsert replaces every issue field and clears the previous link. An optional ADR supplies the new link, independently of the issue body's text, matching `DecisionIndex.put`. `lookup_decision` returns a query and its parameters. Its result columns contain the issue fields followed by the ADR fields, with null ADR fields for an unlinked issue. A missing issue returns no row. No lookup calls GitHub.

Tests execute the schema and statements with Python's standard SQLite module, adapting only parameter placeholders. This checks table creation, constraints, and replacement behavior without a live database or a new dependency. It doesn't validate execution on a Postgres server.

TECH-DEBT: Old ADR snapshots remain after link replacement. This slice leaves database connection management, migrations, and snapshot cleanup to later work.
