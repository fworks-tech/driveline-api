#!/bin/sh
set -e

max_attempts="${MIGRATE_RETRY_ATTEMPTS:-12}"
retry_delay="${MIGRATE_RETRY_DELAY_SECONDS:-2}"
attempt="1"

echo "Running database migrations before startup..."
while true; do
  if python manage.py migrate --noinput 2>/dev/null; then
    echo "✓ Database migrations completed successfully"
    break
  fi

  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "⚠ Database migrations failed after ${max_attempts} attempts"
    echo "⚠ Starting app anyway - you can fix DATABASE_URL and run migrations manually:"
    echo "  python manage.py migrate"
    break
  fi

  echo "Migration attempt ${attempt}/${max_attempts} failed; retrying in ${retry_delay}s..."
  attempt=$((attempt + 1))
  sleep "$retry_delay"
done

exec "$@"