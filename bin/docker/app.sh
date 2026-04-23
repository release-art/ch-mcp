#!/bin/bash -ex

THIS_DIR=$(dirname "${BASH_SOURCE[0]}")
PROJECT_ROOT=$(realpath "${THIS_DIR}/../..")
BIN_DIR="${PROJECT_ROOT}/bin"
cd "${PROJECT_ROOT}"

export BUILDKIT_PROGRESS=plain
export AZURITE_HOSTNAME="azurite"

echo -ne "\033]0;Web UI\007"

exec "${BIN_DIR}/run.sh" docker compose run \
    -it --rm --service-ports \
    --build \
    'app'