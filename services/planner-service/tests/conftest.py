"""Test path bootstrap for planner-service MVP."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_PATH = ROOT / "packages" / "contracts"
SERVICE_PATH = Path(__file__).resolve().parents[1]

for path in (CONTRACTS_PATH, SERVICE_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
