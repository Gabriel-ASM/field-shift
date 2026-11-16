#!/usr/bin/env bash
# Rebuild the image and restart the app on the machine that runs it, keeping what the running app assembled.
#
# The municipalities assembled on demand live inside the container. Before it is replaced, their files are copied
# back into data/, so the new image is built with them.   Usage (in the project folder): docker/redeploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${FIELD_SHIFT_CONTAINER:-field-shift-app}"
IMAGE="${FIELD_SHIFT_IMAGE:-field-shift:non}"
PORT="${FIELD_SHIFT_PORT:-127.0.0.1:8000}"

if docker inspect "$NAME" >/dev/null 2>&1; then
    # Not data/v2: the container regenerates it from these when it starts.
    for folder in profiles raw catalog reference; do
        docker cp -q "$NAME:/app/data/$folder/." "data/$folder/"
    done
    echo "kept $(ls data/profiles | grep -vc README) profiles from the running app"
fi
# --target base: the product; the legacy builder would otherwise also build the `dev` stage.
docker build --target base -t "$IMAGE" . > docker-build.log 2>&1 || { tail -n 30 docker-build.log; exit 1; }
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --restart unless-stopped -p "$PORT:8000" -v field-shift-mongo:/data/db "$IMAGE" >/dev/null
for _ in $(seq 120); do
    curl -sf -o /dev/null "http://${PORT/0.0.0.0/127.0.0.1}/health" && { echo "up: $(curl -s "http://${PORT/0.0.0.0/127.0.0.1}/profiles" | grep -o '"id"' | wc -l) profiles"; exit 0; }
    sleep 1
done
echo "the app did not answer in 120 s"; docker logs --tail 20 "$NAME"; exit 1
