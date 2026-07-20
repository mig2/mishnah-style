"""Path configuration for the entities pipeline webapp."""

import sys
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Key directories
ENTITIES_DIR = ROOT / "entities"
DATA_DIR = ENTITIES_DIR / "data"
DETECT_DIR = ENTITIES_DIR / "detect"
SCHEMA_DIR = ENTITIES_DIR / "schema"
MASECHOT_DIR = ROOT / "masechot"
SCRIPTS_DIR = ROOT / "scripts"

# Make scripts importable
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
