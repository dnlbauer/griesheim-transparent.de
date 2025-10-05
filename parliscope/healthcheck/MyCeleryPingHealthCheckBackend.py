from celery.app import app_or_default  # type: ignore
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


# This health check was copied from:
# https://github.com/revsys/django-health-check/blob/master/health_check/contrib/celery_ping/backends.py
# and modified to use app_or_default() instead of default_app to get the current Celery app.
class MyCeleryPingHealthCheckBackend(BaseHealthCheckBackend):
    critical_service = True
    CORRECT_PING_RESPONSE = {"ok": "pong"}

    def identifier(self) -> str:
        return "MyCeleryPingHealthCheck"

    def check_status(self) -> None:
        app = app_or_default()
        try:
            ping_result: list[dict] | None = app.control.ping(timeout=3)
        except OSError as e:
            self.add_error(ServiceUnavailable("IOError"), e)
        except NotImplementedError as exc:
            self.add_error(
                ServiceUnavailable(
                    "NotImplementedError: Make sure CELERY_RESULT_BACKEND is set"
                ),
                exc,
            )
        except BaseException as exc:
            self.add_error(ServiceUnavailable("Unknown error"), exc)
        else:
            if not ping_result:
                self.add_error(
                    ServiceUnavailable("Celery workers unavailable"),
                )
            else:
                self._check_ping_result(ping_result)

    def _check_ping_result(self, ping_result: list) -> None:
        active_workers = []

        for result in ping_result:
            worker, response = list(result.items())[0]
            if response != self.CORRECT_PING_RESPONSE:
                self.add_error(
                    ServiceUnavailable(
                        f"Celery worker {worker} response was incorrect"
                    ),
                )
                continue
            active_workers.append(worker)

        if not self.errors:
            self._check_active_queues(active_workers)

    def _check_active_queues(self, active_workers: list) -> None:
        app = app_or_default()
        defined_queues = getattr(app.conf, "task_queues", None) or getattr(
            app.conf, "CELERY_QUEUES", None
        )

        if not defined_queues:
            return

        defined_queues = {queue.name for queue in defined_queues}
        active_queues = set()

        for queues in app.control.inspect(active_workers).active_queues().values():  # type: ignore
            active_queues.update([queue.get("name") for queue in queues])

        for queue in defined_queues.difference(active_queues):
            self.add_error(
                ServiceUnavailable(f"No worker for Celery task queue {queue}"),
            )
