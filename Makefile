init:
	uv sync --extra dev

run:
	uv run python chatbot.py

check:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run python -m unittest discover tests

.PHONY: check init run test
