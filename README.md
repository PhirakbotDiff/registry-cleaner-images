# Registry Cleaner Images

A Python tool to automatically clean up old Docker images from a Docker Registry v2, keeping the latest tags and running garbage collection. Supports multiple repositories and basic authentication.

## 🗑️ Features

- Delete old tags while keeping the last N tags
- Automatically skip the `latest` tag
- Supports multiple repositories
- Basic authentication (username/password)
- Optional garbage collection after cleanup
- Robust error handling for missing tags or failed requests
- Configurable via `.env` file

## :rocket: Installation

```bash
git clone <your-repo-url>
cd registry-clean_images
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✅  Configuration

Create a `.env` file:

```bash
REGISTRY_URL=http://your-registry:5000
REGISTRY_USER=admin
REGISTRY_PASS=secret
KEEP_LAST=7
REGISTRY_CONTAINER=registry
REGISTRY_CONFIG_PATH=/etc/docker/registry/config.yml
```

## Usage
```python registry_cleanup.py```

## ⚠️ Notes

* Ensure delete.enabled: true in your registry config.
* Garbage collection may lock the registry during large cleanups.
* For self-signed certificates, warnings can be suppressed in the script.


## Cron Example

`Run daily at 3 AM:`

```bash
0 3 * * * /usr/bin/python3 /path/to/registry_cleanup.py >> /var/log/registry_cleanup.log 2>&1
```