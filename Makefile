.PHONY: setup run build clean lint test

VENV       := .venv
ARGS       ?=

# ── Platform detection ───────────────────────────────────────
ifeq ($(OS),Windows_NT)
    PYTHON_SYS ?= python
    PYTHON     := $(VENV)/Scripts/python
    PIP        := $(VENV)/Scripts/pip
else
    PYTHON_SYS ?= python3
    PYTHON     := $(VENV)/bin/python
    PIP        := $(VENV)/bin/pip
endif

# ── Targets ──────────────────────────────────────────────────
setup:
	$(PYTHON_SYS) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo ""
	@echo "✓ venv ready. Run:  make run ARGS=\"download -u 'URL'\""

run:
	$(PYTHON) -m h1tool $(ARGS)

build:
	$(PYTHON) -m PyInstaller \
		--onefile \
		--name h1tool \
		--clean \
		h1tool/__main__.py

lint:
	$(PYTHON) -m ruff check h1tool/

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf $(VENV) dist build *.spec __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true