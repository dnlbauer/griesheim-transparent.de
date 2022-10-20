#!/bin/sh
set -e

# Collect static files
#echo "Collect static files"
#python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

if [ "$1" = crond ]; then
  echo "Registering cron job"
  python manage.py crontab add
fi

# running command
echo "running $@"
exec $@
