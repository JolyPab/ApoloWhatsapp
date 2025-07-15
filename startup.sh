#!/bin/bash
echo "--- Running startup.sh ---"
echo "Current directory: $(pwd)"

echo "--- Checking Environment Variables ---"
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
  echo "AZURE_OPENAI_API_KEY is NOT set."
else
  echo "AZURE_OPENAI_API_KEY is SET."
fi

if [ -z "$GOOGLE_CREDENTIALS_JSON" ]; then
  echo "GOOGLE_CREDENTIALS_JSON is NOT set."
else
  echo "GOOGLE_CREDENTIALS_JSON is SET."
fi

if [ -z "$APIFY_TOKEN" ]; then
  echo "APIFY_TOKEN is NOT set."
else
  echo "APIFY_TOKEN is SET."
fi

echo "--- Listing contents of /home/site/wwwroot ---"
ls -la /home/site/wwwroot

export PYTHONPATH="/home/site/wwwroot"
echo "PYTHONPATH is set to: $PYTHONPATH"

echo "--- Starting Gunicorn with debug logging ---"
exec gunicorn --bind=0.0.0.0:$PORT --workers=1 --log-level=debug --access-logfile - --error-logfile - whatsapp_bot:app
