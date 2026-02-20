import requests # type: ignore
from datetime import datetime
import os
import subprocess
import json
import urllib3 # type: ignore
from dotenv import load_dotenv # type: ignore

# Load .env variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Registry config
REGISTRY_URL = os.getenv("REGISTRY_URL")
KEEP_LAST = int(os.getenv("KEEP_LAST", 5))
USERNAME = os.getenv("REGISTRY_USER")
PASSWORD = os.getenv("REGISTRY_PASS")
REGISTRY_CONTAINER = os.getenv("REGISTRY_CONTAINER", "registry")
CONFIG_PATH = os.getenv("REGISTRY_CONFIG_PATH", "/etc/docker/registry/config.yml")

HEADERS = {
    "Accept": (
        "application/vnd.docker.distribution.manifest.v2+json,"
        "application/vnd.docker.distribution.manifest.list.v2+json,"
        "application/vnd.oci.image.manifest.v1+json,"
        "application/vnd.oci.image.index.v1+json"
    )
}
AUTH = (USERNAME, PASSWORD) 

def list_repositories():
    """List all repositories in registry"""
    url = f"{REGISTRY_URL}/v2/_catalog"
    resp = requests.get(url, auth=AUTH, cert=False, verify=False)
    resp.raise_for_status()
    return resp.json().get("repositories", [])

def list_tags(repo):
    url = f"{REGISTRY_URL}/v2/{repo}/tags/list"
    resp = requests.get(url, auth=AUTH, cert=False, verify=False)
    resp.raise_for_status()
    return resp.json().get("tags", [])

def get_manifest_digest(repo, tag):
    url = f"{REGISTRY_URL}/v2/{repo}/manifests/{tag}"
    try:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)  # disable SSL verify if needed
        if resp.status_code == 404:
            print(f"⚠️ Manifest not found for {repo}:{tag}")
            return None
        resp.raise_for_status()
        return resp.headers.get("Docker-Content-Digest")
    except requests.RequestException as e:
        print(f"❌ Failed to get manifest for {repo}:{tag}: {e}")
        return None

def delete_manifest(repo, digest):
    url = f"{REGISTRY_URL}/v2/{repo}/manifests/{digest}"
    resp = requests.delete(url, auth=AUTH, cert=False, verify=False)
    if resp.status_code == 202:
        print(f"✅ Deleted digest {digest} in repo {repo}")
    else:
        print(f"❌ Failed to delete {digest} in repo {repo}: {resp.status_code}")

def get_tag_creation_date(repo, tag):
    """
    Get the creation date of a tag in a Docker Registry.
    - Returns datetime.now() for 'latest' or if request fails.
    """
    if tag == "latest":
        return datetime.now()

    url = f"{REGISTRY_URL}/v2/{repo}/manifests/{tag}"
    try:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, verify=False)  # cert=False is not a valid arg
        if resp.status_code == 404:
            print(f"⚠️ Tag not found: {repo}:{tag}")
            return datetime.now()
        resp.raise_for_status()
        manifest = resp.json()
        # Try to extract creation date
        created = manifest.get("history", [])[0]
        if created:
            created_json = json.loads(created.get("v1Compatibility", "{}"))
            created_date = created_json.get("created")
            if created_date:
                return datetime.fromisoformat(created_date.replace("Z", "+00:00"))
        # Fallback if history or created is missing
        return datetime.now()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch tag {repo}:{tag}: {e}")
        return datetime.now()
    except Exception as e:
        print(f"⚠️ Error parsing manifest for {repo}:{tag}: {e}")
        return datetime.now()

def cleanup_repo(repo):
    tags = list_tags(repo)
    if not tags or len(tags) <= KEEP_LAST:
        print(f"No tags to delete in repo {repo}")
        return

    tags_with_date = [(tag, get_tag_creation_date(repo, tag)) for tag in tags]
    tags_sorted = sorted(tags_with_date, key=lambda x: x[1], reverse=True)
    to_delete = tags_sorted[KEEP_LAST:]

    for tag, date in to_delete:
        print(f"Deleting tag: {tag} (created: {date}) in repo {repo}")
        digest = get_manifest_digest(repo, tag)
        delete_manifest(repo, digest)

def run_garbage_collect():
    print("Running garbage collection...")
    try:
        subprocess.run(
            ["docker", "exec", REGISTRY_CONTAINER, "registry", "garbage-collect", CONFIG_PATH],
            check=True
        )
        print("✅ Garbage collection completed.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Garbage collection failed: {e}")

if __name__ == "__main__":
    
    repos = list_repositories()

    for repo in repos:
        print(f"Cleaning up repository: {repo}")
        # if str(repo) == 'release-api':
        cleanup_repo(repo)

    run_garbage_collect()
