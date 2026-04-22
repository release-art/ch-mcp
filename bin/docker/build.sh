#!/bin/bash -ex

THIS_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "${THIS_DIR}/../..")

export BUILDKIT_PROGRESS=plain

cd "${PROJECT_ROOT}"
docker build . -t ch-mcp:local-latest -f Dockerfile