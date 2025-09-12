import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class SetupPeriodicTasksCommandTest(TestCase):
    """Test cases for the setup_periodic_tasks management command."""

    def setUp(self) -> None:
        """Clean up any existing tasks before each test."""
        PeriodicTask.objects.filter(name="update-solr-index").delete()
        CrontabSchedule.objects.all().delete()

    def tearDown(self) -> None:
        """Clean up after each test."""
        PeriodicTask.objects.filter(name="update-solr-index").delete()

    def test_create_periodic_task_with_defaults(self) -> None:
        """Test creating a periodic task with default arguments."""
        out = StringIO()
        call_command("setup_periodic_tasks", stdout=out)

        # Verify task was created
        task = PeriodicTask.objects.get(name="update-solr-index")
        self.assertEqual(task.task, "parliscope.tasks.indexing.update_solr_index")
        self.assertTrue(task.enabled)

        # Verify cron schedule (default: 0 3 * * *)
        schedule = task.crontab
        self.assertEqual(schedule.minute, "0")
        self.assertEqual(schedule.hour, "3")
        self.assertEqual(schedule.day_of_month, "*")
        self.assertEqual(schedule.month_of_year, "*")
        self.assertEqual(schedule.day_of_week, "*")

        # Verify kwargs are properly JSON serialized
        kwargs = json.loads(task.kwargs)
        expected_kwargs = {
            "force": False,
            "allow_ocr": True,
            "chunk_size": 10,
        }
        self.assertEqual(kwargs, expected_kwargs)

        # Verify output
        output = out.getvalue()
        self.assertIn("Created cron schedule", output)
        self.assertIn("Created periodic task: update-solr-index", output)
        self.assertIn("enabled=True", output)

    def test_create_periodic_task_with_custom_arguments(self) -> None:
        """Test creating a periodic task with custom arguments."""
        out = StringIO()
        call_command(
            "setup_periodic_tasks",
            "--schedule",
            "*/15 * * * *",
            "--chunk_size",
            "25",
            "--force",
            "--no-ocr",
            "--disable",
            stdout=out,
        )

        # Verify task was created
        task = PeriodicTask.objects.get(name="update-solr-index")
        self.assertFalse(task.enabled)  # disabled

        # Verify custom cron schedule (*/15 * * * *)
        schedule = task.crontab
        self.assertEqual(schedule.minute, "*/15")
        self.assertEqual(schedule.hour, "*")

        # Verify custom kwargs
        kwargs = json.loads(task.kwargs)
        expected_kwargs = {
            "force": True,
            "allow_ocr": False,  # --no-ocr inverts to False
            "chunk_size": 25,
        }
        self.assertEqual(kwargs, expected_kwargs)

        # Verify output
        output = out.getvalue()
        self.assertIn("enabled=False", output)
        self.assertIn("force=True", output)
        self.assertIn("allow_ocr=False", output)
        self.assertIn("chunk_size=25", output)

    def test_update_existing_periodic_task(self) -> None:
        """Test updating an existing periodic task."""
        # Create initial task
        initial_schedule = CrontabSchedule.objects.create(
            minute="0", hour="2", day_of_month="*", month_of_year="*", day_of_week="*"
        )
        PeriodicTask.objects.create(
            name="update-solr-index",
            crontab=initial_schedule,
            task="parliscope.tasks.indexing.update_solr_index",
            kwargs='{"force": false, "allow_ocr": false, "chunk_size": 5}',
            enabled=False,
        )

        # Update with new settings
        out = StringIO()
        call_command(
            "setup_periodic_tasks",
            "--schedule",
            "0 4 * * *",
            "--chunk_size",
            "20",
            stdout=out,
        )

        # Verify task was updated
        task = PeriodicTask.objects.get(name="update-solr-index")
        self.assertTrue(task.enabled)  # should be enabled now

        # Verify updated schedule
        schedule = task.crontab
        self.assertEqual(schedule.hour, "4")

        # Verify updated kwargs
        kwargs = json.loads(task.kwargs)
        expected_kwargs = {
            "force": False,
            "allow_ocr": True,
            "chunk_size": 20,
        }
        self.assertEqual(kwargs, expected_kwargs)

        # Verify output
        output = out.getvalue()
        self.assertIn("Updated periodic task: update-solr-index", output)

    def test_invalid_cron_expression(self) -> None:
        """Test handling of invalid cron expressions."""
        out = StringIO()
        with self.assertRaises(SystemExit):  # Command should exit with error
            call_command(
                "setup_periodic_tasks", "--schedule", "invalid cron", stdout=out
            )

        output = out.getvalue()
        self.assertIn("Invalid cron expression", output)

    def test_cron_schedule_reuse(self) -> None:
        """Test that existing cron schedules are reused."""
        # Create a schedule first
        existing_schedule = CrontabSchedule.objects.create(
            minute="0", hour="6", day_of_month="*", month_of_year="*", day_of_week="*"
        )
        initial_count = CrontabSchedule.objects.count()

        # Create task with same schedule
        out = StringIO()
        call_command("setup_periodic_tasks", "--schedule", "0 6 * * *", stdout=out)

        # Verify schedule count didn't increase (reused existing)
        self.assertEqual(CrontabSchedule.objects.count(), initial_count)

        # Verify the task uses the existing schedule
        task = PeriodicTask.objects.get(name="update-solr-index")
        self.assertEqual(task.crontab, existing_schedule)

        output = out.getvalue()
        self.assertIn("Using existing cron schedule", output)

    def test_kwargs_json_serialization(self) -> None:
        """Test that kwargs are properly JSON serialized."""
        call_command("setup_periodic_tasks", "--chunk_size", "15", "--force")

        task = PeriodicTask.objects.get(name="update-solr-index")

        # Verify kwargs is valid JSON string
        self.assertIsInstance(task.kwargs, str)
        kwargs = json.loads(task.kwargs)

        # Verify all expected keys and types
        self.assertIn("force", kwargs)
        self.assertIn("allow_ocr", kwargs)
        self.assertIn("chunk_size", kwargs)

        self.assertIsInstance(kwargs["force"], bool)
        self.assertIsInstance(kwargs["allow_ocr"], bool)
        self.assertIsInstance(kwargs["chunk_size"], int)
