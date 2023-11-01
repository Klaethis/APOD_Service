import os

WORKERS = int(os.environ.get('WORKERS', 4))

bind = f'0.0.0.0:5000'
workers = WORKERS