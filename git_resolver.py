import json
from pathlib import Path
from urllib.parse import urlparse
from github import Github, GithubException
from globals import SCRIPT_DIR
import configparser

config = configparser.ConfigParser()
config.read(SCRIPT_DIR / "config.ini")

print(config.sections())

g = Github(config['GITHUBPAT']['token'])

RESERVED = {
    "settings", "login", "logout", "features", "about",
    "pricing", "site", "contact", "security", "orgs",
    "search", "marketplace", "explore", "topics", "new",
    "notifications", "session"
}

def classify_github_link(link: str):
    link = link.strip()
    
    if not link.startswith(("http://", "https://")):
        link = "https://" + link

    u = urlparse(link)

    host = u.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    
    if host != "github.com":
        raise ValueError(f"Invalid domain: {host}. Only github.com is supported.")

    path = u.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    
    parts = [p for p in path.split("/") if p]

    if not parts:
        raise ValueError("Root GitHub URL provided, specific profile or repo required.")

    owner = parts[0]

    if owner.lower() in RESERVED:
        raise ValueError(f"'{owner}' is a reserved GitHub system path, not a user.")

    if len(parts) == 1:
        return ("profile", owner, None)

    repo_name = parts[1]
    return ("repo", owner, repo_name)


def resolve(link: str):
    try:
        kind, owner, repo = classify_github_link(link)
    except ValueError as e:
        print(f"Error parsing link: {e}")
        return

    if kind == "profile":
        return resolve_profile(owner)

    elif kind == "repo":
        return resolve_repo(owner, repo)

    else:
        raise ValueError("Unsupported GitHub link type")


def resolve_profile(owner_name: str):
    print(f"Resolving Profile: {owner_name}...")
    
    entity = get_github_entity(owner_name)
    print(f"Found: {entity} (Type: {type(entity).__name__})")
    
    repos = entity.get_repos()
    for r in repos:
        print(r.name)

    return entity


def get_github_entity(name: str):
    # Try User first
    try:
        return g.get_user(name)
    except GithubException as e:
        if e.status != 404:
            raise e 

    # Try Organization if User failed
    try:
        return g.get_organization(name)
    except GithubException as e:
        if e.status == 404:
            raise ValueError(f"User or Organization '{name}' not found on GitHub.")
        raise e


def resolve_repo(owner: str, repo_name: str):
    full_name = f"{owner}/{repo_name}"
    print(f"Resolving Repo: {full_name}...")
    
    try:
        repo = g.get_repo(full_name)
        return repo
    except GithubException as e:
        if e.status == 404:
            raise ValueError(f"Repository {full_name} not found.")
        raise e