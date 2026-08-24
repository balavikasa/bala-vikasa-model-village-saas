.PHONY: install dev migrate import-workbook test lint run purge zip

install:
	python -m pip install -r requirements-dev.txt

dev:
	flask --app wsgi run --debug --host 0.0.0.0 --port 5000

migrate:
	flask --app wsgi db upgrade

import-workbook:
	flask --app wsgi import-master-data data/MV-Master-Data-26-27.xlsx

test:
	pytest

lint:
	ruff check .

run:
	gunicorn --config gunicorn.conf.py wsgi:app

purge:
	flask --app wsgi purge-recycle-bin

zip:
	python scripts/package_release.py
