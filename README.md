# CamDesign

CamDesign is a field-friendly Flask workspace for preparing rough security-camera quote plans from a user-supplied map or site-plan image.

The first vertical slice supports creating and resuming projects, uploading a base image, placing camera field-of-view cones, capturing project notes, and autosaving the versioned document to SQLite.

## Set up

```powershell
uv sync
uv run flask --app camdesign db-upgrade
uv run flask --app camdesign run
```

Open <http://127.0.0.1:5000>. The development server is for local development only.

Runtime data is written to `data/camdesign.sqlite3` and `data/uploads/`. It is intentionally ignored by Git.

## Quality gate

```powershell
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Current scope

- Project dashboard and resumable projects
- PNG, JPEG, and WebP site-image uploads
- Camera placement by clicking or dragging a field-of-view cone
- Adjustable field-of-view for new cameras
- General onsite project notes
- SQLite persistence with optimistic revision checks

Cable runs, MDF/IDF markers, linked notes, richer editing, and deterministic PDF export are planned next; their controls are labeled as upcoming rather than presented as working features.
