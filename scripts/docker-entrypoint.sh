#!/bin/sh
set -eu

max_attempts="${MIGRATE_RETRY_ATTEMPTS:-12}"
retry_delay="${MIGRATE_RETRY_DELAY_SECONDS:-2}"
attempt="1"

echo "Running database migrations before startup..."
while true; do
  if python manage.py migrate --noinput; then
    break
  fi

  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database migrations failed after ${max_attempts} attempts."
    exit 1
  fi

  echo "Migration attempt ${attempt} failed; retrying in ${retry_delay}s..."
  attempt=$((attempt + 1))
  sleep "$retry_delay"
done

exec "$@"