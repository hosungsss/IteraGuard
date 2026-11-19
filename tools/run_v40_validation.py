"""Backward CLI compatibility; forwards to current validation runner."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("run_v41_validation.py")),run_name="__main__")
