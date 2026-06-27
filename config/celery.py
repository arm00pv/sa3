import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('saas_optimizer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'nightly-bank-sync': {
        'task': 'core.tasks.sync_bank_feeds',
        'schedule': crontab(hour=2, minute=0),  # Runs at 2:00 AM every night
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
