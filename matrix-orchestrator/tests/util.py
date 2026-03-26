from __future__ import annotations

import importlib.util
import pathlib


def load_script_module(script_filename: str, module_name: str):
    script_path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "scripts"
        / script_filename
    )
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
