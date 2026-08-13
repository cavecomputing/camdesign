# CamDesign

CamDesign is a field-friendly Flask workspace for turning site images into rough security-camera quote plans. It currently supports resumable projects, camera field-of-view placement, onsite notes, and debounced SQLite autosave.

## Start locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the project root:

```powershell
uv sync --frozen
uv run flask --app app db-upgrade
uv run flask --app app run
```

Open <http://127.0.0.1:5000>. Stop the server with `Ctrl+C`. On later starts, only the final command is normally needed; rerun `db-upgrade` after pulling schema changes.

## Connect from another device

On a trusted local network, bind the development server to the computer's network interfaces:

```powershell
uv run flask --app app run --host 0.0.0.0
```

Run `ipconfig`, find the computer's IPv4 address, then open `http://<IPv4-address>:5000` on the other device. If Windows prompts, allow access only on Private networks. This development server is not hardened for public internet exposure.

## Data and checks

Runtime data lives in `data/camdesign.sqlite3` and `data/uploads/`; both are ignored by Git.

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
