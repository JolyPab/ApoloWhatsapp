#!/bin/bash

# Активируем виртуальное окружение
source /home/site/wwwroot/venv/bin/activate

# Переходим в директорию с приложением
cd /home/site/wwwroot

# Запускаем Gunicorn
echo "--- Starting Gunicorn with virtual environment ---"
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 whatsapp_bot:app
