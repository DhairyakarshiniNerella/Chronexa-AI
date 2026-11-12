
from apscheduler.schedulers.background import BackgroundScheduler

from app.reminder_checker import check_due_reminders


# Create background scheduler
scheduler = BackgroundScheduler()


def start_scheduler():

    # Run reminder checker every minute.
    # Prevent overlapping executions of this job.
    scheduler.add_job(
        check_due_reminders,
        trigger="interval",
        minutes=1,
        id="reminder_checker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30
    )

    if not scheduler.running:
        scheduler.start()

    print("Chronexa reminder scheduler started!")


def stop_scheduler():

    if scheduler.running:
        scheduler.shutdown(wait=True)
        print("Chronexa reminder scheduler stopped!")
