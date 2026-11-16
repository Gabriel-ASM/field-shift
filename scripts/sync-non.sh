#!/usr/bin/env bash
# Mirror this working copy to the machine that runs it (ssh host "non"), once or continuously.
#
#   scripts/sync-non.sh            one sync
#   scripts/sync-non.sh --watch    sync again whenever a file changes (inotifywait, or every 2 s without it)
#
# Code goes from here to there. What the remote generates stays there and is never overwritten or deleted:
# downloaded raw data, the profiles assembled beyond the three examples, their catalog and the derived references.
set -euo pipefail

HOST="${FIELD_SHIFT_REMOTE_HOST:-non}"
DIR="${FIELD_SHIFT_REMOTE_DIR:-field-shift-ctrlaltespaco}"
cd "$(dirname "$0")/.."

sync() {
    rsync -az --delete \
        --exclude='.git/' --exclude='.venv/' --exclude='.pytest_cache/' --exclude='__pycache__/' \
        --exclude='node_modules/' --exclude='ctrlaltespaco/dist/' --exclude='.env' --exclude='*.part' \
        --exclude='/data/raw/ibge/pam/' --exclude='/data/raw/nasa_power/cells/' \
        --exclude='/data/raw/soilgrids/municipalities/' --exclude='/data/raw/mapa-siszarc/by-uf/' \
        --exclude='/data/raw/mapa-siszarc/municipalities/' \
        --include='/data/profiles/ariquemes-ro/***' --include='/data/profiles/franca-sp/***' \
        --include='/data/profiles/varginha-mg/***' --include='/data/profiles/README.md' --exclude='/data/profiles/*' \
        --exclude='/data/v2/' --exclude='/data/catalog/perfis-exemplo.json' \
        --exclude='/data/reference/crop-data-coverage.json' --exclude='/data/reference/crop-markov-coverage.json' \
        --exclude='/data/reference/economic-benchmarks.json' --exclude='/data/reference/economic-input-coverage.json' \
        ./ "$HOST:$DIR/"
    echo "$(date +%T) synced to $HOST:$DIR"
}

sync
[ "${1:-}" = "--watch" ] || exit 0
if command -v inotifywait >/dev/null; then
    while inotifywait -qq -r -e modify,create,delete,move --exclude '(\.git/|node_modules|__pycache__|\.venv|/dist/)' .; do
        sleep 0.3      # let an editor finish writing several files
        sync || true
    done
else
    while sleep 2; do
        rsync_changes=$(find . -newer .git/sync-non.stamp -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path './.venv/*' 2>/dev/null | head -1 || true)
        [ -e .git/sync-non.stamp ] && [ -z "$rsync_changes" ] && continue
        touch .git/sync-non.stamp
        sync || true
    done
fi
