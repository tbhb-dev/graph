#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

set -euo pipefail

temporal_dev_server_start() {
  local port attempt
  TEMPORAL_SERVER_PID=
  for ((port = 17233; port < 17333; port++)); do
    if ! (echo >"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
      break
    fi
  done
  if ((port == 17333)); then
    echo "No free Temporal port found" >&2
    return 1
  fi

  "$TEMPORAL" server start-dev --headless --port "$port" >"$TEST_TMPDIR/temporal-server.log" 2>&1 &
  TEMPORAL_SERVER_PID=$!
  echo "Started Temporal dev server (PID $TEMPORAL_SERVER_PID, port $port)"
  for ((attempt = 0; attempt < 30; attempt++)); do
    if ! kill -0 "$TEMPORAL_SERVER_PID" 2>/dev/null; then
      echo "Temporal dev server exited before becoming healthy" >&2
      cat "$TEST_TMPDIR/temporal-server.log" >&2
      return 1
    fi
    if "$TEMPORAL" operator cluster health --address "127.0.0.1:$port" --command-timeout 1s >"$TEST_TMPDIR/temporal-health.log" 2>&1; then
      echo "Temporal dev server is healthy"
      cat "$TEST_TMPDIR/temporal-health.log"
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for Temporal dev server health" >&2
  cat "$TEST_TMPDIR/temporal-server.log" "$TEST_TMPDIR/temporal-health.log" >&2
  return 1
}

temporal_dev_server_stop() {
  local attempt leaked=0
  if [[ -z ${TEMPORAL_SERVER_PID:-} ]]; then
    return 0
  fi
  kill "$TEMPORAL_SERVER_PID" 2>/dev/null || true
  for ((attempt = 0; attempt < 10; attempt++)); do
    if ! kill -0 "$TEMPORAL_SERVER_PID" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  if kill -0 "$TEMPORAL_SERVER_PID" 2>/dev/null; then
    echo "Temporal dev server leaked after shutdown; killing it" >&2
    kill -KILL "$TEMPORAL_SERVER_PID"
    leaked=1
  fi
  wait "$TEMPORAL_SERVER_PID" || true
  echo "Stopped and reaped Temporal dev server (PID $TEMPORAL_SERVER_PID)"
  TEMPORAL_SERVER_PID=
  return "$leaked"
}
