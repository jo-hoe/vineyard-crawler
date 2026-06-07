# Cross-platform Makefile (Windows / Linux / macOS).
#
# Requires GNU make. On Windows install via Chocolatey (`choco install make`),
# Scoop, or use the one bundled with Git Bash / MSYS2.
#
# Platform-sensitive bits (venv bin/ vs Scripts/, recursive delete) are routed
# through Python so the same recipes work everywhere.

PYTHON ?= python
VENV   ?= .venv

# Detect Windows in a way that works for cmd.exe AND POSIX shells:
# - native cmd.exe / PowerShell sets $(OS) to "Windows_NT"
# - Git Bash / MSYS sets $(MSYSTEM)
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
	PY_EXE   := python.exe
else ifdef MSYSTEM
	VENV_BIN := $(VENV)/Scripts
	PY_EXE   := python.exe
else
	VENV_BIN := $(VENV)/bin
	PY_EXE   := python
endif

PIP    := $(VENV_BIN)/pip
PY     := $(VENV_BIN)/$(PY_EXE)

OUTPUT ?= vineyards.csv

.PHONY: init update test start docs clean help

help:
	@$(PYTHON) -c "print('targets: init, update, test, start, docs, clean')"

init:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

update:
	$(PY) -m pip install --upgrade -e ".[dev]"

test:
	$(PY) -m pytest

start:
	$(PY) main.py --output $(OUTPUT)

docs:
	$(PY) generate_cli_docs.py

# Portable recursive remove: shells out to Python so we don't depend on
# `rm` (POSIX) or `rmdir /s /q` (cmd) being available.
clean:
	$(PYTHON) -c "import shutil, pathlib; \
	[shutil.rmtree(p, ignore_errors=True) for p in ['$(VENV)', '.pytest_cache']]; \
	[shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
