from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from .tasks import check_for_new_requests


def start():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Executa a tarefa a cada 5 minutos
    scheduler.add_job(check_for_new_requests, 'interval', minutes=5, jobstore='default')
    
    scheduler.start()
