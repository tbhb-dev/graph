# Agent instructions

Graph is the public Apache-2.0 repository for the `tbhbgraph` plugin.

- Start work on a branch and use Conventional Commits without `Signed-off-by` or `Co-authored-by` trailers.
- Keep infrastructure identifiers, internal paths, private repository names, and secrets out of repository files and pull requests.
- Fill the pull request template and keep the local draft out of commits.

## Checks

Run `mise install`, `uv sync`, and `bazelisk run //:bazel_env` to prepare the tools. Install this clone's Git hooks with `tbhbdev alpha install --hooks-only`.

Run `bazelisk test //...` and `bazelisk run //:format`. Keep branch coverage at 100%.
