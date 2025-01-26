from django.core.management.base import BaseCommand
from processing.schedulers import start


class Command(BaseCommand):
    help = 'Start the scheduler for processing analysis requests'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting scheduler...")
        start()
