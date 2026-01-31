import typer
import asyncio
import json
from typing import Optional
from detector import detect_async
from loc_resolver import resolve as resolve_loc
from git_resolver import resolve as resolve_git
from importlib import import_module
from importlib import import_module

from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich import box
from rich.rule import Rule

from globals import ERRORS

app = typer.Typer()
console = Console()

def print_report(scan_result):
    """
    Renders a clean, two-part report: 
    1. Detailed breakdown of vulnerabilities (if any).
    2. A summary table of all packages scanned.
    """
    ecosystem = scan_result.get("ecosystem", "Unknown")
    packages = scan_result.get("packages", [])
    
    vulnerable_pkgs = [p for p in packages if p.get("vulnerabilities")]
    
    if vulnerable_pkgs:
        console.print(Rule(f"[bold red]Vulnerability Details ({len(vulnerable_pkgs)} packages affected)", style="red"))
        console.print("") 

        for pkg in vulnerable_pkgs:
            pkg_name = pkg.get('name', 'Unknown')
            pkg_ver = pkg.get('version', '?')
            purl = pkg.get('purl', '')
            
            vuln_texts = []
            for v in pkg['vulnerabilities']:
                vid = v.get('id')
                summary = v.get('summary') or "No summary provided."
                fixed_in = v.get('safe_version')
                
                v_render = f"[bold red]{vid}[/bold red]: {summary} "
                if fixed_in:
                    v_render += f"\n[bold green]↪ Fix available: {fixed_in}[/bold green]"
                else:
                    v_render += f"\n[dim italic]↪ No fix version identified[/dim italic]"
                
                vuln_texts.append(v_render)
            
            # panel_content = "\n\n[dim]─[/dim]\n\n".join(vuln_texts)
            panel_content = "\n\n".join(vuln_texts)
            
            console.print(Panel(
                panel_content,
                title=f"[bold white]{pkg_name}[/bold white] [cyan]@{pkg_ver}[/cyan]",
                subtitle=f"[dim]{purl}[/dim]",
                border_style="red",
                box=box.ROUNDED,
                expand=True,
                padding=(1, 2)
            ))
            console.print("") 

    console.print(Rule("[bold blue]Scan Summary", style="blue"))
    
    table = Table(
        box=box.SIMPLE, 
        header_style="bold cyan", 
        collapse_padding=True,
        pad_edge=False,
        expand=True
    )
    
    table.add_column("Package", style="white")
    table.add_column("Version", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Vulns", justify="right")
    table.add_column("Action", style="green")

    sorted_packages = sorted(packages, key=lambda x: x.get("isdirect", False), reverse=True)
    sorted_packages = sorted(sorted_packages, key=lambda x: len(x.get('vulnerabilities', [])), reverse=True)

    for pkg in sorted_packages:
        vulns = pkg.get("vulnerabilities", [])
        count = len(vulns)

        if pkg['isdirect']:
            if count > 0:
                status = "[bold red]✖[/bold red]"
                fix_versions = [v['safe_version'] for v in vulns if v['safe_version']]
                if fix_versions:
                    action = f"Upgrade to {fix_versions[0]}" 
                else:
                    action = "Check Details"
                vuln_str = f"[red]{count}[/red]"
            else:
                status = "[bold green]✔[/bold green]"
                action = "[dim]-[/dim]"
                vuln_str = "[dim]0[/dim]"

            table.add_row(
                pkg.get("name"),
                pkg.get("version"),
                status,
                vuln_str,
                action
            )
        else:
            if count > 0:
                status = "[red]✖[/red]"
                fix_versions = [v["safe_version"] for v in vulns if v.get("safe_version")]
                if fix_versions:
                    action = f"[green]Upgrade to {fix_versions[0]}[/green]"
                else:
                    action = "[red]Check Details[/red]"
                vuln_str = f"[red]{count}[/red]"
            else:
                status = "[dim green]✔[/dim green]"
                action = "[dim]-[/dim]"
                vuln_str = "[dim]0[/dim]"
            
            table.add_row(
                f"[dim white]{pkg.get("name")}[/dim white]",
                f"[dim white]{pkg.get("version")}[/dim white]",
                status,
                vuln_str,
                action
            )

    console.print(table)
    
    total_vulns = sum(len(p.get('vulnerabilities', [])) for p in packages)
    if total_vulns == 0:
        console.print(f"\n[bold green]No vulnerabilities found in {len(packages)} packages.[/bold green]\n")
    else:
        console.print(f"\n[bold red]Found {total_vulns} vulnerabilities in {len(vulnerable_pkgs)} packages.[/bold red]️\n")

def run(git: bool = False, link: Optional[str] = None):
    try:
        if git:
            if not link:
                raise Exception("Link required")
            ecosystem_info = resolve_git(link)
        else:
            ecosystem_info = resolve_loc()
    except Exception as e:
        return json.dumps({
            "error": "unsupported-ecosystem"
        })
    
    try:
        module = import_module(f"parsers.{ecosystem_info['name'].lower()}_parser")
    except Exception as e:
        return json.dumps({
            "error": "parser-module-not-found"
        })

    parsed = module.parse(ecosystem_info)
    directpkgs = [pkg for pkg in parsed['packages'] if pkg.get('isdirect')]
    indirectpkgs = [pkg for pkg in parsed['packages'] if not pkg.get('isdirect')]

    try:
        scan_results = asyncio.run(detect_async(parsed))
        return json.dumps(scan_results)
    except:
        return json.dumps({
            "error": "osv-connection-failed"
        })

@app.command(name="run")
def run_pretty_print(git: bool = False, link: Optional[str] = None):
    try:
        if git:
            if not link:
                raise Exception("Link required")
            ecosystem_info = resolve_git(link)
        else:
            ecosystem_info = resolve_loc()
    except Exception as e:
        console.print()
        console.print(f"[bold red]{e}[/bold red]")
        console.print(ERRORS['unsupported-ecosystem'])
        return
    
    console.print()
    console.print(f" Ecosystem : [bold cyan]{ecosystem_info['name']}[/bold cyan]")
    console.print(f" Target    : [green]{ecosystem_info['path']}[/green]")

    try:
        module = import_module(f"parsers.{ecosystem_info['name'].lower()}_parser")
    except Exception as e:
        console.print()
        console.print(f"[bold red]{e}[/bold red]")
        console.print(ERRORS['unsupported-ecosystem'])
        return

    parsed = module.parse(ecosystem_info)
    directpkgs = [pkg for pkg in parsed['packages'] if pkg.get('isdirect')]
    indirectpkgs = [pkg for pkg in parsed['packages'] if not pkg.get('isdirect')]
    
    console.print(f" Found     : [white]{len(directpkgs)}[/white] direct, [white]{len(indirectpkgs)}[/white] transitive dependencies")
    console.print()

    with console.status("[bold green]Querying OSV Database...", spinner="dots"):
        try:
            scan_results = asyncio.run(detect_async(parsed))
            print_report(scan_results)
        except:
            console.print("[bold red]Unable to connect to the OSV Database.[/bold red]")
            return

if __name__ == '__main__':
    app()