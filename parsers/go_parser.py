import re
import os

def parse(file_info):
    ecosystem = file_info.get('name')
    file_path = file_info.get('path')
    file_format = file_info.get('format')

    output_data = {
        "ecosystem": ecosystem,
        "packages": []
    }

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return output_data

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        packages = []

        if file_format == 'gomod':
            packages = _parse_go_mod(content)

        elif file_format == 'text' and file_info.get('role') == 'checksum':
            packages = _parse_go_sum(content)

        output_data["packages"] = packages

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return output_data


def _go_purl(name: str, version: str) -> str:
    return f"pkg:golang/{name}@{version}"


def _parse_go_mod(content):
    pkgs_by_name = {}

    lines = content.splitlines()
    in_require_block = False
    skip_block = False  

    for raw_line in lines:
        line = raw_line.strip()

        if not line or line.startswith('//'):
            continue

        if skip_block:
            if line == ')':
                skip_block = False
            continue

        if re.match(r'^(replace|exclude|retract)\s*\($', line):
            skip_block = True
            continue

        if re.match(r'^(replace|exclude|retract)\b', line):
            continue

        if re.match(r'^require\s*\($', line):
            in_require_block = True
            continue

        if in_require_block and line == ')':
            in_require_block = False
            continue

        if re.match(r'^(module\s+|go\s+)', line):
            continue

        parts = re.split(r'\s+', line)

        name = None
        version = None

        if re.match(r'^require\b', line) and not in_require_block:
            if len(parts) >= 3:
                name = parts[1]
                version = parts[2]

        elif in_require_block:
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]

        if not name or not version:
            continue

        is_indirect = bool(re.search(r'//\s*indirect\b', raw_line))
        isdirect = not is_indirect

        existing = pkgs_by_name.get(name)
        if existing:
            if not existing["isdirect"] and isdirect:
                existing["isdirect"] = True
            continue

        pkgs_by_name[name] = {
            "name": name,
            "purl": _go_purl(name, version),
            "version": version,
            "isdirect": isdirect,
        }

    return list(pkgs_by_name.values())


def _parse_go_sum(content):
    """
    Parses go.sum content.
    Emits PURL entries for full resolved graph.
    """
    pkgs = []
    seen = set()

    for raw_line in content.splitlines():
        parts = raw_line.split()
        if len(parts) < 2:
            continue

        name = parts[0].strip()
        version = parts[1].strip()

        if version.endswith("/go.mod"):
            version = version.replace("/go.mod", "")

        key = f"{name}@{version}"
        if key in seen:
            continue
        seen.add(key)

        pkgs.append({
            "name": name,
            "purl": _go_purl(name, version),
            "version": version,
            "isdirect": False,
        })

    return pkgs
