import json
import re
import os

try:
    import yaml
except ImportError:
    yaml = None


def _npm_purl(name: str, version: str) -> str:
    return f"pkg:npm/{name}@{version}"


def parse(file_info):
    ecosystem = file_info.get('name')
    file_path = file_info.get('path')
    file_format = file_info.get('format')
    file_role = file_info.get('role')

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

        if file_format == 'json':
            json_content = json.loads(content)

            if file_role == 'manifest' or file_path.endswith('package.json'):
                packages = _parse_package_json(json_content)
            elif file_role == 'lockfile':
                packages = _parse_npm_lock(json_content)

        elif file_format == 'yarn':
            packages = _parse_yarn_lock(content)

        elif file_format == 'yaml':
            if yaml:
                yaml_content = yaml.safe_load(content)
                packages = _parse_pnpm_lock(yaml_content)
            else:
                print("Error: PyYAML is not installed. Cannot parse pnpm files.")

        output_data["packages"] = packages

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return output_data


def _parse_package_json(data):
    pkgs = []
    groups = ['dependencies', 'devDependencies', 'optionalDependencies']

    for group in groups:
        deps = data.get(group, {})
        for name, version in deps.items():
            pkgs.append({
                "name": name,
                "purl": _npm_purl(name, version),
                "version": version,
                "isdirect": True,
            })
    return pkgs


def _parse_npm_lock(data):
    pkgs_by_name = {}
    direct_names = set()
    direct_versions = {}

    if "packages" in data and "" in data["packages"]:
        root_pkg = data["packages"][""]
        for grp in ("dependencies", "devDependencies", "optionalDependencies"):
            for name, ver in root_pkg.get(grp, {}).items():
                direct_names.add(name)
                direct_versions[name] = ver

    elif "dependencies" in data:
        for name, details in data["dependencies"].items():
            direct_names.add(name)
            if isinstance(details, dict):
                direct_versions[name] = details.get("version", "unknown")
            else:
                direct_versions[name] = details if isinstance(details, str) else "unknown"

    if "packages" in data:
        for path, details in data["packages"].items():
            if path == "":
                continue

            parts = path.split("node_modules/")
            name = parts[-1]
            if not name:
                continue

            name = name.split('/node_modules/')[0]

            version = details.get("version") or direct_versions.get(name, "unknown")
            isdirect = name in direct_names

            existing = pkgs_by_name.get(name)
            if existing:
                if existing["version"] == "unknown" and version != "unknown":
                    existing["version"] = version
                existing["isdirect"] = existing["isdirect"] or isdirect
            else:
                pkgs_by_name[name] = {
                    "name": name,
                    "purl": _npm_purl(name, version),
                    "version": version,
                    "isdirect": isdirect,
                }

    elif "dependencies" in data:
        for name, details in data["dependencies"].items():
            if isinstance(details, dict):
                version = details.get("version", "unknown")
            else:
                version = details if isinstance(details, str) else "unknown"

            isdirect = name in direct_names
            pkgs_by_name[name] = {
                "name": name,
                "purl": _npm_purl(name, version),
                "version": version,
                "isdirect": isdirect,
            }

    for name in direct_names:
        if name not in pkgs_by_name:
            version = direct_versions.get(name, "unknown")
            pkgs_by_name[name] = {
                "name": name,
                "purl": _npm_purl(name, version),
                "version": version,
                "isdirect": True,
            }
        else:
            pkgs_by_name[name]["isdirect"] = True

    return list(pkgs_by_name.values())


def _parse_yarn_lock(content):
    pkgs = []
    lines = content.split('\n')
    current_names = []

    for line in lines:
        if line.startswith('#') or not line.strip():
            continue

        if not line.startswith(' '):
            raw_keys = line.strip().rstrip(':')
            entries = [x.strip() for x in raw_keys.split(',')]

            current_names = []
            for entry in entries:
                match = re.match(r'^"?((?:@[^/]+/)?[^@/"]+)', entry)
                if match:
                    current_names.append(match.group(1))

        elif line.strip().startswith('version') and current_names:
            version = line.split('version', 1)[1].strip().strip('"')

            for name in set(current_names):
                pkgs.append({
                    "name": name,
                    "purl": _npm_purl(name, version),
                    "version": version,
                    "isdirect": False,
                })
            current_names = []

    return pkgs


def _parse_pnpm_lock(data):
    pkgs_by_name = {}
    direct_names = set()
    direct_versions = {}

    if data and "importers" in data:
        for _, details in data["importers"].items():
            for grp in ("dependencies", "devDependencies", "optionalDependencies"):
                deps = details.get(grp, {})
                for name, ver in deps.items():
                    direct_names.add(name)
                    direct_versions[name] = ver

    if data and "packages" in data:
        for pkg_path, details in data["packages"].items():
            clean_path = pkg_path.strip('/')
            parts = clean_path.split('/')

            if parts[0].startswith('@') and len(parts) >= 2:
                name = f"{parts[0]}/{parts[1]}"
                version = parts[2] if len(parts) > 2 else details.get("version", "unknown")
            elif len(parts) >= 2:
                name = parts[0]
                version = parts[1]
            else:
                continue

            isdirect = name in direct_names

            existing = pkgs_by_name.get(name)
            if existing:
                if existing["version"] == "unknown" and version != "unknown":
                    existing["version"] = version
                existing["isdirect"] = existing["isdirect"] or isdirect
            else:
                pkgs_by_name[name] = {
                    "name": name,
                    "purl": _npm_purl(name, version),
                    "version": version,
                    "isdirect": isdirect,
                }

    for name in direct_names:
        if name not in pkgs_by_name:
            version = direct_versions.get(name, "unknown")
            pkgs_by_name[name] = {
                "name": name,
                "purl": _npm_purl(name, version),
                "version": version,
                "isdirect": True,
            }
        else:
            pkgs_by_name[name]["isdirect"] = True

    return list(pkgs_by_name.values())
