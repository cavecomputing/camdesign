CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    client_name TEXT NOT NULL DEFAULT '',
    site_address TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    image_path TEXT NOT NULL,
    image_original_name TEXT NOT NULL,
    image_mime TEXT NOT NULL,
    document_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX projects_updated_at_idx ON projects(updated_at DESC);
