from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from .tasks import check_for_new_requests


def start():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Executa a tarefa a cada 30 segundos (for testing)
    scheduler.add_job(
        check_for_new_requests, "interval", seconds=30, jobstore="default"
    )

    scheduler.start()
