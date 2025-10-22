import os
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
CONFIG = {}
CONFIG["project_dir"] = str(project_dir)
CONFIG["static_resources_dir"] = os.path.join(CONFIG["project_dir"], "src/quinex_utils/parsers/static_resources/")