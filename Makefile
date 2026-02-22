init:
	pip install -r requirements.txt

run:
	python chatbot.py

check:
	ruff format .
	ruff check --fix .

test:
	python -m unittest discover tests

.PHONY: check init run test
