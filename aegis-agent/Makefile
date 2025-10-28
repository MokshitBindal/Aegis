# Makefile for aegis-agent

.PHONY: install lint typecheck test clean

install:
	pip install -r requirements.txt

lint:
	ruff check . --fix

typecheck:
	mypy .

test:
	pytest --cov=. tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +

ci: install lint typecheck test