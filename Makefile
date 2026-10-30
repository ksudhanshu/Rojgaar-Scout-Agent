.PHONY: install test unit integration lint fmt clean

PY ?= .venv/bin/python

install:
	uv venv .venv
	uv pip install --python $(PY) -e ".[dev]"

test:
	mkdir -p reports
	$(PY) -m pytest --junitxml=reports/junit.xml

unit:
	mkdir -p reports
	$(PY) -m pytest tests/unit --junitxml=reports/junit-unit.xml

integration:
	mkdir -p reports
	$(PY) -m pytest tests/integration -m integration --junitxml=reports/junit-integration.xml

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

fmt:
	$(PY) -m ruff format src tests
	$(PY) -m ruff check --fix src tests

clean:
	rm -rf reports .pytest_cache .ruff_cache dist build
