# Vuln

A no-nonsense vulnerability scanner for your dependencies. It parses your package manifests (like `package.json`, `requirements.txt`, etc.) and queries the [OSV database](https://osv.dev/) asynchronously to find known security flaws.

## Features

- **Auto-detection**: Finds supported manifest files in your current directory automatically.
- **Async Scanning**: Queries vulnerabilities in parallel for speed.
- **Rich Output**: Clean terminal tables and panels showing exactly what's broken and how to fix it.
- **Direct & Transitive**: Identifies if the vulnerability is in your code or deep in your dependency tree.

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/itsneoweo/Vuln.git
   cd Vuln
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install typer rich httpx packaging
   ```

## Usage

Navigate to a project folder you want to scan and run the tool:

```bash
# From inside the Vuln directory
python main.py scan
```

The tool will:
1. Detect your lockfile or manifest.
2. Parse the dependency tree.
3. Check against the OSV database.
4. Print a report with upgrade suggestions.

## Make it usable (The Alias)

Typing the full path to the python script every time is annoying. Add an alias to your shell configuration (`.bashrc`, `.zshrc`, etc.) to run it from anywhere.

**Add this line to your config:**

```bash
# Replace /absolute/path/to/Vuln with the actual path
alias vuln="/absolute/path/to/Vuln/venv/bin/python /absolute/path/to/Vuln/main.py"
```

**Reload your shell:**
```bash
source ~/.zshrc  # or ~/.bashrc
```

**Now just run:**
```bash
vuln scan
```