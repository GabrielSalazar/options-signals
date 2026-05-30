import os
import glob
import re

def update_imports(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        replacements = {
            r"from config import": "from backend.core.config import",
            r"import config": "from backend.core import config",
            r"from cache import": "from backend.core.cache import",
            r"from core_engine import": "from backend.services.core_engine import",
            r"from data_providers import": "from backend.services.data_providers import",
            r"from backtest import": "from backend.services.backtest import",
            r"from scoring import": "from backend.domain.scoring import",
            r"from indicators import": "from backend.domain.indicators import",
            r"from greeks import": "from backend.domain.greeks import",
            r"from options_math import": "from backend.domain.options_math import",
        }
        
        for old, new in replacements.items():
            content = re.sub(old, new, content)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

py_files = glob.glob("backend/**/*.py", recursive=True) + glob.glob("tests/*.py") + ["main.py"]

for f in py_files:
    if os.path.isfile(f) and not f.endswith("refactor.py"):
        update_imports(f)
