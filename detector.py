import json
import asyncio
import httpx
from packaging.version import Version
from collections import defaultdict

def _gen_request(ecosystem, package):
    return {
        "package": {
            "purl": package["purl"],
        },
    }

async def fetch_vuln(client: httpx.AsyncClient, query):
    vuln_id, purl = query
    try:
        r = await client.get(f"https://api.osv.dev/v1/vulns/{vuln_id}")
        r.raise_for_status()
    except httpx.HTTPError:
        return None

    vuln = r.json()

    matched = None
    for affected in vuln.get("affected", []):
        affected_purl = affected.get("package", {}).get("purl")
        if affected_purl and (affected_purl in purl or purl in affected_purl):
            matched = affected
            break

    if not matched:
        return None

    safe_version = None
    for r in matched.get("ranges", []):
        if r.get("type") != "SEMVER":
            continue

        for e in r.get("events", []):
            fixed = e.get("fixed")
            if not fixed:
                continue

            try:
                v = Version(fixed)
            except Exception:
                continue
            
            if safe_version is None or v > safe_version:
                safe_version = v

    return {
        "id": vuln["id"],
        "summary": vuln.get("summary"),
        "details": vuln.get("details"),
        "affected": matched,
        "published": vuln.get("published"),
        "modified": vuln.get("modified"),
        "references": vuln.get("references", []),
        "safe_version": str(safe_version) if safe_version else None,
        "_purl_key": purl 
    }

async def detect_async(parsed):
    batch_queries = []

    for package in parsed["packages"]:
        payload = _gen_request(parsed["ecosystem"], package)
        batch_queries.append(payload)

    payload = {"queries": batch_queries}

    timeout = httpx.Timeout(30.0, connect=10.0)
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    async with httpx.AsyncClient(http2=True, timeout=timeout, limits=limits) as client:
        response = await client.post("https://api.osv.dev/v1/querybatch", json=payload)
        response.raise_for_status()

        results = response.json().get("results", [])
        vulns_query = []

        for i, item in enumerate(results):
            if item and "vulns" in item:
                for vuln in item["vulns"]:
                    vulns_query.append((vuln["id"], parsed["packages"][i]["purl"]))

        tasks = [fetch_vuln(client, query) for query in vulns_query]
        vuln_datas = await asyncio.gather(*tasks)

        vuln_lookup = defaultdict(dict)
        
        for data in vuln_datas:
            if data:
                key = (data['id'], data['_purl_key'])
                clean_data = {k: v for k, v in data.items() if k != '_purl_key'}
                vuln_lookup[key] = clean_data

        packages = []
        for i, package in enumerate(parsed["packages"]):
            pkg = package.copy() 
            pkg["vulnerabilities"] = []
            
            if i < len(results) and results[i] and "vulns" in results[i]:
                for v_item in results[i]["vulns"]:
                    v_id = v_item["id"]
                    purl = pkg["purl"]
                    
                    detail = vuln_lookup.get((v_id, purl))
                    if detail:
                        pkg["vulnerabilities"].append(detail)
            
            packages.append(pkg)

        final_response = {
            "ecosystem": parsed["ecosystem"],
            "packages": packages
        }

        return final_response