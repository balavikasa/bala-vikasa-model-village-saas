#!/bin/sh
set -eu

flask --app wsgi db upgrade
exec "$@"
