#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

set -euo pipefail

TEMPORAL="$PWD/$1"
# shellcheck source=tests/lib/temporal_dev_server.sh
source "$TEST_SRCDIR/$TEST_WORKSPACE/tests/lib/temporal_dev_server.sh"
trap 'temporal_dev_server_stop || exit 1' EXIT

temporal_dev_server_start
