"""
Celery configuration for the Tech Debt Analyzer.
"""
import os

# Redis configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery broker and result backend
broker_url = redis_url
result_backend = redis_url

# Serialization settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# Timezone settings
timezone = 'UTC'
enable_utc = True

# Worker configuration
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000

# Result backend settings
result_expires = 3600  # 1 hour

# Task execution settings
task_soft_time_limit = 300  # 5 minutes
task_time_limit = 600  # 10 minutes