# O-RAN Agent Harness, professional entry points.
# See README.md for the full walkthrough and scenarios/README.md for the demo narrative.

.PHONY: install verify demo test clean help

help:
	@echo "O-RAN Agent Harness, available targets:"
	@echo "  make install   pip install the package in editable mode with test extras"
	@echo "  make verify    run the 10-check verify gate (scripts/verify.py)"
	@echo "  make demo      walk both scenarios end-to-end (scripts/demo.sh)"
	@echo "  make test      alias for verify (the verify gate IS the test suite)"
	@echo "  make clean     remove __pycache__ trees and *.pyc files"
	@echo ""
	@echo "Quick start: make install && make verify && make demo"

install:
	pip install -e '.[test]'

verify:
	python3 scripts/verify.py

demo:
	./scripts/demo.sh

test: verify

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
