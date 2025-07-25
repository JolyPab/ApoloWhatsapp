#!/bin/bash
export GUNICORN_CMD_ARGS="--timeout 600 --access-logfile -"
gunicorn app:app 