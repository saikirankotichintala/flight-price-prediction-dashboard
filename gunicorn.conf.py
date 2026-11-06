"""Conservative worker settings for the in-memory dataset and tree ensembles."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
threads = 2
worker_class = "gthread"
timeout = 120
accesslog = "-"
errorlog = "-"
