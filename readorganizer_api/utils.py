import celery


dispatch_task_by_name = celery.current_app.send_task
