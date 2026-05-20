.PHONY: install test lint format check backtest paper status clean

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests
	mypy src

format:
	ruff format src tests
	ruff check --fix src tests

check: lint test

backtest:
	trading-bot backtest -s momentum -u sector_etfs --start 2018-01-01

paper:
	trading-bot paper -s momentum --dry-run

status:
	trading-bot status

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
