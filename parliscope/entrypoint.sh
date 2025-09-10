#!/bin/bash
set -e

if [ "$1" != "celery" ] && [ "$1" != "crond" ]; then
  echo "Collect static files"
  python manage.py collectstatic --no-input --clear
fi

echo "Apply database migrations"
python manage.py migrate --noinput

if [ "$1" = crond ]; then
  echo "Registering cron job"
  python manage.py crontab add
fi

# running command
echo "running $@"
exec $@
