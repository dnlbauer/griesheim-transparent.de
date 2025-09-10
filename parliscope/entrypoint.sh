#!/bin/bash

echo "Collect static files"
python manage.py collectstatic --no-input --clear

echo "Apply database migrations"
python manage.py migrate --noinput
python manage.py migrate --noinput --database=scraped

if [ "$1" = crond ]; then
  echo "Registering cron job"
  python manage.py crontab add
fi

# running command
echo "running $@"
exec $@
