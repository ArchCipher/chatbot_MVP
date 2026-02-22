init:
	pip install -r requirements.txt

run:
	python chatbot.py

fmt:
	black .

test:
	python -m unittest discover tests

.PHONY: fmt init run test
