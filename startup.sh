#!/bin/sh
gunicorn --bind=0.0.0.0 --timeout 600 whatsapp_bot:app
