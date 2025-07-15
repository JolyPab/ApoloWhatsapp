#!/bin/bash

# Добавляем корень сайта в PYTHONPATH, так как все зависимости теперь находятся там
export PYTHONPATH=$PYTHONPATH:/home/site/wwwroot

# Запускаем Gunicorn с увеличенным таймаутом для надежности
echo "--- Starting Gunicorn ---"
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --log-level debug "whatsapp_bot:app"
