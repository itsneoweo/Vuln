import json
from pathlib import Path
from globals import CONFIG

def detect_ecosystem():
    ecosystems = CONFIG["ecosystems"]

    for ecosystem in ecosystems:
        for marker in ecosystem["detect"]:
            if Path(marker).exists():
                return ecosystem

    return None

def resolve():
    ecosystem = detect_ecosystem()
    if ecosystem is None:
        raise RuntimeError("Undefined Ecosystem: Could not detect ecosystem")
    dep_srcs = sorted(ecosystem["files"], key=lambda f: f["priority"], reverse=True)

    for dep_src in dep_srcs:
        path = dep_src['path']
        if Path(path).exists():
            return {
                "name": ecosystem["name"],
                **dep_src
            }

    raise RuntimeError("Undefined Dependencies: Could not determine the source of dependencies")