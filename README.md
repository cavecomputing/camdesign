# CamDesign

CamDesign is a field-friendly Flask workspace for turning site images into rough security-camera quote plans. It currently supports resumable projects, camera field-of-view placement, onsite notes, and debounced SQLite autosave.

## Start locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then double-click
`start-camdesign.bat`. It migrates the database, starts the server, and opens
<http://127.0.0.1:5000> in the default browser. Closing the console window stops it.

On first run it writes `data/secret.key`, a stable signing key so that restarting the
server does not invalidate sessions in tabs that are already open. Keep that file.

To reach the app from a phone or tablet on the same trusted network, run
`start-camdesign.bat lan`, which binds all interfaces and prints the URLs to use.

To run the same steps by hand:

```powershell
uv sync --frozen
uv run flask --app app db-upgrade
uv run app.py
```

`uv run app.py` runs the entry-point script in the project's managed environment and is equivalent to `uv run python app.py`. Open <http://127.0.0.1:5000> and stop the server with `Ctrl+C`. On later starts, only the final command is normally needed; rerun `db-upgrade` after pulling schema changes.

For Flask debug mode and automatic reloading during development, use:

```powershell
uv run flask --app app run --debug
```

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
