# CamDesign

CamDesign is a field-friendly Flask workspace for turning site images into rough security-camera quote plans. It currently supports resumable projects, camera field-of-view placement, per-camera and project notes, and debounced SQLite autosave.

**Supported on desktop and tablet only.** The editor is built for a mouse or a
large touch screen at 768px wide and up. Phone-width layouts are not supported and
are not tested; use a laptop or a tablet in landscape onsite.

## Editing a plan

| Action | How |
| --- | --- |
| Pick a tool | Click it, or press `1` for Select and `2` for Camera |
| Place a camera | With Camera armed, click for a default cone or drag to aim it. The tool stays armed for the next one |
| Move a camera | Drag the circle at the cone's point |
| Aim and set reach | Drag anywhere inside the cone: around to aim, in and out for reach |
| Name it and add a note | Select it, then use the **Selected camera** panel |
| Change field of view | 30–180°. With Camera armed it sets the next one; with Select active it retargets the selected camera |
| Set make and model | Type into the dropdowns to search them. Hanwha adds a WAVE License dropdown. Like field of view, the pick carries to the next camera placed |
| Delete | `Delete` or `Backspace`, or the sidebar button |
| Undo | `Ctrl+Z`, or the arrow in the header |
| Deselect and put the tool down | `Escape` — clears the selection and returns to Select. With a dropdown open, the first press just closes it |
| Zoom and pan | Scroll to zoom at the cursor, double-click to fit. Drag empty canvas or middle-drag anywhere to pan |

Changes autosave a moment after you stop. If a save fails the header says so and
keeps retrying on its own, so a brief dead spot on the network does not lose work.

## Start locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then double-click
`start-camdesign.bat`. It migrates the database, starts the server, and opens
<http://127.0.0.1:5000> in the default browser. Closing the console window stops it.

On first run it writes `data/secret.key`, a stable signing key so that restarting the
server does not invalidate sessions in tabs that are already open. Keep that file.

To reach the app from a tablet on the same trusted network, run
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

## Connect from a tablet

On a trusted local network, bind the development server to the computer's network interfaces:

```powershell
uv run flask --app app run --host 0.0.0.0
```

Run `ipconfig`, find the computer's IPv4 address, then open `http://<IPv4-address>:5000` on the tablet. If Windows prompts, allow access only on Private networks. This development server is not hardened for public internet exposure.

Use a tablet in landscape. Below 768px the inspector controls are cramped and the
plan image is too small to place cameras accurately, so phones are out of scope.

## Data and checks

Runtime data lives in `data/camdesign.sqlite3` and `data/uploads/`; both are ignored by Git.

The equipment offered in the Make / Model / License dropdowns is plain CSV under
`catalog/`, one file per brand, re-read on every page load — see
[catalog/README.md](catalog/README.md) to correct a spec or add a vendor.

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
