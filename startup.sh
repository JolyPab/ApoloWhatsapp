#!/bin/bash

# Каталог для локальных пакетов
PACKAGE_DIR="/home/site/wwwroot/__app_packages__"

# Проверяем, существует ли маркерный файл (например, из Flask), чтобы понять, была ли уже установка.
# Если его нет, значит, это первый запуск.
if [ ! -f "$PACKAGE_DIR/flask/__init__.py" ]; then
    echo "--- First-time setup: Installing dependencies from requirements.txt into $PACKAGE_DIR ---"
    
    # Создаем каталог для пакетов
    mkdir -p $PACKAGE_DIR
    
    # Устанавливаем зависимости
    pip install --target=$PACKAGE_DIR -r /home/site/wwwroot/requirements.txt
    
    # Проверяем, что установка прошла успешно
    if [ $? -ne 0 ]; then
        echo "--- ERROR: pip install failed. Aborting startup. ---"
        exit 1
    fi
    
    echo "--- Installation complete. ---"
else
    echo "--- Dependencies already installed, skipping installation. ---"
fi

# Добавляем каталог с пакетами в PYTHONPATH, чтобы Python мог их найти
export PYTHONPATH=$PYTHONPATH:$PACKAGE_DIR

# Запускаем Gunicorn с увеличенным таймаутом для надежности
echo "--- Starting Gunicorn ---"
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --log-level debug "whatsapp_bot:app"
