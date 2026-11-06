"""Load the prototype under its own package name, never shadowing backend app modules."""

import importlib
import importlib.util
import sys
from pathlib import Path

from dotenv import load_dotenv

PROTOTYPE = Path(__file__).resolve().parents[3] / "prototypes" / "records-analysis"
PACKAGE = "campus_records_prototype"
load_dotenv(PROTOTYPE.parents[1] / ".env")

if PACKAGE not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        PACKAGE,
        PROTOTYPE / "app" / "__init__.py",
        submodule_search_locations=[str(PROTOTYPE / "app")],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)

analysis = importlib.import_module(f"{PACKAGE}.analysis")
progress = importlib.import_module(f"{PACKAGE}.progress")
routes = importlib.import_module(f"{PACKAGE}.routes")
