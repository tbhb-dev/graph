-- SPDX-License-Identifier: Apache-2.0
-- Copyright Tony Burns

CREATE TABLE decision_issues (
    repository TEXT NOT NULL,
    number BIGINT NOT NULL,
    node_id TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    body TEXT NOT NULL,
    comments TEXT NOT NULL,
    PRIMARY KEY (repository, number)
);

CREATE TABLE adrs (
    repository TEXT NOT NULL,
    path TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (repository, path, commit_sha)
);

CREATE TABLE decision_adr_links (
    repository TEXT NOT NULL,
    number BIGINT NOT NULL,
    adr_path TEXT NOT NULL,
    adr_commit TEXT NOT NULL,
    PRIMARY KEY (repository, number),
    FOREIGN KEY (repository, number)
        REFERENCES decision_issues (repository, number),
    FOREIGN KEY (repository, adr_path, adr_commit)
        REFERENCES adrs (repository, path, commit_sha)
);
