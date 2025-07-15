#!/bin/bash
export PYTHONPATH="/home/site/wwwroot"
exec gunicorn --bind=0.0.0.0:8080 --workers=4 --timeout 600 whatsapp_bot:app
