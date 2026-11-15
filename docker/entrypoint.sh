#!/bin/bash
# Start MongoDB (reachable only from inside the container), load the data, then serve the API and the front.
set -euo pipefail

MONGO_LOG=/var/log/mongodb/mongod.log
mkdir -p /data/db "$(dirname "$MONGO_LOG")"
chown -R mongodb:mongodb /data/db "$(dirname "$MONGO_LOG")"

gosu mongodb mongod --bind_ip 127.0.0.1 --dbpath /data/db --logpath "$MONGO_LOG" --logappend &
mongo_pid=$!

for _ in $(seq 60); do
    mongosh --quiet --eval 'db.adminCommand("ping").ok' >/dev/null 2>&1 && break
    kill -0 "$mongo_pid" 2>/dev/null || { echo "mongod exited during start:"; tail -n 20 "$MONGO_LOG"; exit 1; }
    sleep 0.5
done
mongosh --quiet --eval 'db.adminCommand("ping").ok' >/dev/null || { echo "mongod did not answer in 30 s"; exit 1; }

# Idempotent: installs the collection validators and upserts chains and profiles.
gosu app python -m field_shift.ingest --mongo "$FIELD_SHIFT_MONGO_URI" --database "$FIELD_SHIFT_DB"

gosu app uvicorn --factory field_shift.api:create_app --host 0.0.0.0 --port 8000 &
api_pid=$!

stopping=0
stop() { stopping=1; kill -TERM "$api_pid" 2>/dev/null || true; }
trap stop TERM INT

status=0
wait "$api_pid" || status=$?        # returns early when a signal arrives
if [ "$stopping" = 1 ]; then
    wait "$api_pid" 2>/dev/null || true
    status=0                        # a requested stop is a clean exit
fi

kill -TERM "$mongo_pid" 2>/dev/null || true
wait "$mongo_pid" || true
echo "mongod stopped"
exit "$status"
