.PHONY: setup assets data test eval demo clean help

PYTHON := python
PIP := pip
VENV := .venv
VENV_PYTHON := $(VENV)/Scripts/python.exe
VENV_PIP := $(VENV)/Scripts/pip.exe

help:
	@echo "TRACE-FX Makefile"
	@echo ""
	@echo "  make setup   - Create venv and install dependencies"
	@echo "  make assets  - Verify vendored vis-network exists"
	@echo "  make data    - Generate synthetic datasets"
	@echo "  make test    - Run pytest"
	@echo "  make eval    - Run evaluation on all seeds"
	@echo "  make demo    - Launch Streamlit demo"
	@echo "  make clean   - Remove generated outputs"

setup:
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e .
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) freeze > requirements.lock.txt
	@echo "Setup complete. Activate with: .venv\\Scripts\\activate"

assets:
	@echo "Checking vendored assets..."
	@if exist "app\assets\vis-network.min.js" (echo "vis-network.min.js found") else (echo "WARNING: vis-network.min.js missing. Run: python scripts/vendor_assets.py")
	@if exist "app\assets\vis-network.min.css" (echo "vis-network.min.css found") else (echo "WARNING: vis-network.min.css missing.")

data:
	@echo "Generating synthetic datasets..."
	$(PYTHON) -m tracefx data
	@echo "Data generation complete."

test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -q --tb=short

eval:
	@echo "Running evaluation..."
	$(PYTHON) -m tracefx eval --data-dir data --out reports
	@echo "Results saved to reports/eval_results.csv"

demo:
	@echo "Launching TRACE-FX demo..."
	$(PYTHON) -m streamlit run app/app.py

clean:
	@echo "Cleaning generated outputs..."
	if exist reports rmdir /s /q reports
	if exist __pycache__ rmdir /s /q __pycache__
	if exist .pytest_cache rmdir /s /q .pytest_cache
	@echo "Clean complete (data/ and src/ preserved)."
