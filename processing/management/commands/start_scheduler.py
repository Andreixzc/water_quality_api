from django.core.management.base import BaseCommand
from processing.schedulers import start
import time


class Command(BaseCommand):
    help = "Start the scheduler for processing analysis requests"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting scheduler...")
        start()

        # Manter o processo vivo
        try:
            while True:
                time.sleep(
                    1
                )  # Aguarda 1 segundo para evitar sobrecarga de CPU
        except KeyboardInterrupt:
            self.stdout.write("Scheduler stopped.")
