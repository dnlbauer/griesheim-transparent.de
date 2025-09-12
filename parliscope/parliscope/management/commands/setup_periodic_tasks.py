import json
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Setup periodic tasks for Celery Beat scheduler"

    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commit

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--schedule",
            default="0 3 * * *",
            help="Cron schedule for Solr index updates (default: daily at 3 AM)",
        )
        parser.add_argument(
            "--chunk_size",
            help=f"chunk size for sending documents to solr (default: {self.DEFAULT_CHUNK_SIZE})",
            type=int,
            default=self.DEFAULT_CHUNK_SIZE,
        )
        parser.add_argument(
            "--force",
            help="force update for all documents in periodic task",
            action="store_true",
        )
        parser.add_argument(
            "--no-ocr",
            help="disallow ocr for documents (takes a long time)",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "--disable",
            help="disable the periodic task (default: task is enabled)",
            action="store_true",
            default=False,
        )

    def handle(self, **options: Any) -> None:
        schedule_expr: str = options["schedule"]
        chunk_size: int = options["chunk_size"]
        force: bool = options["force"]
        allow_ocr: bool = not options["no_ocr"]  # inverted logic like update_solr.py
        enabled: bool = not options["disable"]  # inverted logic - default is enabled

        # Parse cron expression
        try:
            minute, hour, day_of_month, month_of_year, day_of_week = (
                schedule_expr.split()
            )
        except ValueError:
            self.stdout.write(
                self.style.ERROR(
                    f"Invalid cron expression: {schedule_expr}. "
                    "Expected format: 'minute hour day_of_month month_of_year day_of_week'"
                )
            )
            raise SystemExit(1) from None

        # Create or get the cron schedule
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created cron schedule: {schedule}"))
        else:
            self.stdout.write(f"Using existing cron schedule: {schedule}")

        # Create or update the periodic task
        task_name = "update-solr-index"
        kwargs_json = json.dumps(
            {
                "force": force,
                "allow_ocr": allow_ocr,
                "chunk_size": chunk_size,
            }
        )

        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                "crontab": schedule,
                "task": "parliscope.tasks.indexing.update_solr_index",
                "kwargs": kwargs_json,
                "enabled": enabled,
            },
        )

        if not created:
            # Update existing task
            periodic_task.crontab = schedule
            periodic_task.kwargs = kwargs_json
            periodic_task.enabled = enabled
            periodic_task.save()
            self.stdout.write(self.style.SUCCESS(f"Updated periodic task: {task_name}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created periodic task: {task_name}"))

        self.stdout.write(
            f"Task configured with schedule: {schedule_expr} "
            f"(enabled={enabled}, force={force}, chunk_size={chunk_size}, allow_ocr={allow_ocr})"
        )
