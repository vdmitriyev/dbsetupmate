#!/bin/sh

echo "Generating SSL"
python cli.py generate-ssl

echo "Starting web application ..."
exec "$@"