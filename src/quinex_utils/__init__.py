from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
CONFIG = {}
CONFIG["static_resources_dir"] = MODULE_DIR / "parsers/static_resources/"