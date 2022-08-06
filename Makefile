.DEFAULT_GOAL := full-run

.PHONY: requirements
requirements:
	pip3 install -r requirements.txt

.PHONY: dev-requirements
dev-requirements: requirements
	pip3 install -r dev-requirements.txt

.PHONY: tests
tests: dev-requirements
	pytest

.PHONY: run
run: requirements
	python3 -m aggregator.app

.PHONY: full-run
full-run: tests run
