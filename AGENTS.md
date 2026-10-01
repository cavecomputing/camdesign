# AGENTS.md

## Mission

Build a reliable, maintainable Flask web app for designing networks on site plans: placing and documenting cameras, cable runs, network closets, and other network equipment on blueprint designs, then exporting the result as a quote or design package. Security-camera quoting is the first workflow shipped, not the product's boundary. Prefer a small, well-tested vertical slice over broad scaffolding or speculative features. Keep geometry, persistence, HTTP, and rendering concerns separate so each can evolve independently.

## Instruction priority

- Follow the user's current request first, then this file, then established repository conventions.
- Read the relevant code, tests, configuration, and `git status` before editing. Do not guess at APIs or project state.
- If a request conflicts with these guardrails or requires a major architectural/dependency change, explain the tradeoff and get approval before proceeding.
- Keep plans and changes proportional to the task. Do not redesign unrelated code.

## Scope and product boundaries

- The product is a general network design tool. Camera placement and quoting came first; cabling, MDF/IDF and other network equipment are part of the same design surface, so name things (UI copy, modules, schema) for network design rather than camera quoting unless the code is genuinely camera-specific.
- The first workflow is: create a client project, add one or more building/floor plans from user-supplied images or PDFs, mark up each plan, save and resume the work, then export a polished PDF package (a quote today, design documentation as it grows).
- Optimize the initial product for a field technician or estimator assembling a rough, trustworthy design and quote package onsite. Favor fast capture, large touch-friendly controls, obvious save state, and useful notes over CAD-level precision or equipment-catalog complexity.
- Target desktop and tablet only, at 768px wide and up. Phone-width layouts are out of scope: do not add phone breakpoints, and do not compromise the desktop editor to accommodate one. Below 768px the plan image is too small to place cameras accurately.
- Use `assets/ui-direction-light-estimator.png` as the visual direction: warm off-white workspace, ink-navy typography, restrained blue/coral accents, generous spacing, and a map-first layout. Treat it as inspiration rather than a pixel-perfect specification.
- Keep the hierarchy explicit: a project represents the client/site engagement; a plan represents one building, floor, or area and owns its source asset, address/location label, markup document, notes, and revision. Do not overload one project row with a single plan.
- List plans in the editor's left sidebar with a readable plan name and address/location subtext. Adding a plan starts a focused upload flow that captures or confirms both values; a plan may inherit the project's site address but remains independently editable.
- Preserve an uploaded PDF as an immutable source. Markup operates on deterministic rasterized page assets; never draw directly into an embedded browser PDF. A selected PDF page becomes a plan, and a multi-page PDF may create multiple plans only through an explicit user choice.
- The initial markup vocabulary is deliberately small: cameras with a source point and field-of-view cone, Ethernet cable runs, MDF/IDF locations, and notes. Keep these symbols minimal, legible, and visually consistent in both the editor and PDF.
- A camera placement stores a normalized anchor point, direction, range, and field-of-view angle. Click placement may use sensible defaults; dragging from the source point sets direction/range. Field-of-view angle remains explicitly adjustable.
- Cable runs are ordered normalized points with style/label metadata, not pixels painted onto the source image. MDF/IDF markers and every other item use the same document-coordinate system.
- General project notes belong to the project. Item-linked notes may be represented in the document model, but do not lock in a callout/numbering UI until that workflow is designed and tested with real quotes.
- The uploaded map image is an immutable project asset by default. Markup remains separate so editing, undo/redo, restyling, and high-quality export do not degrade the source image.
- Export must be deterministic from saved project data and include the plan, legend, project metadata, and selected notes. Do not make browser screenshots the canonical PDF implementation.
- Treat the blueprint document as the core domain: document metadata, units, levels/pages, geometry, symbols, annotations, and revision/version metadata.
- Keep the canonical document format serializable and versioned. Validate it at every persistence and API boundary. Never make canvas or DOM objects the stored domain model.
- Separate domain operations from presentation. Geometry calculations, snapping, transforms, selection, undo/redo commands, and serialization must not depend on Flask request globals or DOM APIs.
- Preserve backward compatibility for stored documents. Any schema change needs an explicit migration path and fixtures covering old and new versions.
- Do not add collaboration, real-time sync, CAD interoperability, billing, accounts, cloud storage, background jobs, or a frontend framework unless the task explicitly requires it.
- Google Maps acquisition is out of scope initially: accept an image the user is authorized to use. Do not scrape map tiles or add a Maps API without explicit approval and a licensing/attribution review.
- Avoid speculative abstractions. Extract a reusable interface after a second real use case, or sooner when needed to isolate an external service or make behavior testable.

## Target architecture

Use a `src` layout and an application factory. The expected shape is:

```text
app.py                 # single, thin application entry point
src/camdesign/
  __init__.py          # create_app(config=None)
  config.py            # configuration classes/loading only
  extensions.py        # unbound extension objects; initialized in create_app
  blueprints/
    editor/             # editor pages and editor-specific endpoints
    projects/           # project/document workflows
    api/                # versioned JSON endpoints, when actually needed
  domain/               # framework-independent blueprint model and operations
  services/             # use-case orchestration and transaction boundaries
  repositories/         # persistence interfaces and implementations
  templates/
  static/
    js/
    css/
tests/
  unit/
  integration/
```

- `app.py` is the only application entry point at the repository root. It may import `create_app`, expose `app`, and launch local development, but it must not contain routes, configuration logic, database access, or business behavior.
- `create_app` owns configuration, extension initialization, blueprint registration, error handlers, logging, and CLI registration.
- Define extension objects without binding them globally; call `init_app` inside the factory.
- Organize blueprints by user-facing capability, not by HTTP verb. Keep route handlers thin: parse and validate input, call a service, and translate the result to HTTP.
- Do not put business logic, database transactions, or large queries in routes, templates, or CLI commands.
- Avoid module-level mutable state and import-time I/O. Use `current_app` only at the Flask boundary; pass explicit values deeper into the application.
- Generate URLs with `url_for`. Namespace blueprint templates to avoid collisions.
- APIs belong under `/api/v1` once exposed. Use a consistent JSON error shape and correct status codes; never leak tracebacks or internal exception text.

## Python and Flask conventions

- Use `uv` exclusively for Python versions, virtual environments, dependency resolution, locking, and command execution. Keep project metadata in `pyproject.toml` and commit `uv.lock`.
- Run project commands with `uv run ...`; use `uv add` / `uv remove` for dependencies and `uv sync` to materialize the locked environment. Do not use bare `pip`, create a second environment, maintain `requirements.txt`, or hand-edit `uv.lock`.
- Pin the supported Python range in `pyproject.toml` and keep `.python-version` consistent when present.
- Add type hints to public functions and domain/service boundaries. Prefer dataclasses or validated schema objects for domain data over loose dictionaries.
- Keep functions cohesive, use descriptive names, and favor explicit dependencies over hidden globals.
- Configuration comes from environment variables or instance configuration. Commit a safe `.env.example`, never a real `.env`, credential, production URL, or secret key.
- Use database migrations for schema changes. Never silently create or mutate a production schema at app startup.
- Bound queries and request sizes. Paginate collection endpoints and avoid N+1 database access.
- Use structured, actionable logging. Do not log secrets, session contents, full blueprint payloads, or sensitive user data.
- Do not use Flask's development server or debug mode in production. Production deployment must use a supported WSGI server and explicit proxy/timeout/resource configuration.

## Frontend conventions

### HTML and accessibility

- Prefer semantic server-rendered HTML and progressive enhancement. A user should get a useful error or fallback when JavaScript fails.
- All controls must be keyboard reachable, visibly focused, and labeled. Preserve sensible tab order and use ARIA only where native semantics are insufficient.
- Treat canvas as a view, not the sole interface. Provide accessible names/status text for important editor actions and expose non-canvas controls for editable properties.

### JavaScript

- Use native ES modules via `<script type="module">`; do not add a bundler until a concrete need justifies it.
- Use one small page entry module and focused modules such as `api/`, `state/`, `geometry/`, `rendering/`, `commands/`, and `components/` as they become necessary.
- Prefer named exports, explicit imports, and pure functions for geometry/state transitions. Avoid globals, inline event handlers, and hidden cross-module side effects.
- Centralize network calls. Check status and content type, handle aborts/timeouts, and surface recoverable errors to the user.
- Use `textContent` and safe DOM construction for untrusted values. Do not use `innerHTML`, `eval`, or dynamic code execution with user-controlled data.
- Event listeners and observers must have clear ownership and cleanup. Animation/render loops must stop when the owning view is disposed or hidden.

### CSS

- Keep a single declared cascade order, for example: `@layer reset, tokens, base, layout, components, utilities, overrides;`.
- Put design tokens (color, spacing, type, elevation, z-index, breakpoints) in custom properties. Components consume tokens rather than inventing one-off values.
- Scope component styles with low-specificity class selectors. Avoid IDs for styling, deep descendant selectors, inline styles, and `!important` except for a documented accessibility or utility exception.
- Split styles by concern/component once a file becomes difficult to navigate; keep the layer order centralized and stable.
- Support responsive layouts from 768px up, zoom, high contrast, reduced motion, and both pointer and keyboard input. Do not encode meaning with color alone.

## Data integrity and security

- Validate and normalize all path, query, form, JSON, and uploaded-file input on the server. Client validation is only a usability aid.
- Use parameterized database access through the chosen data layer. Never concatenate untrusted values into SQL, shell commands, paths, CSS, or HTML.
- Protect every cookie-authenticated state-changing request against CSRF. Use secure session-cookie settings in production (`Secure`, `HttpOnly`, and an appropriate `SameSite` policy).
- Keep Jinja autoescaping enabled. Any use of `Markup`, `|safe`, raw HTML insertion, or CSP relaxation requires a documented justification and a focused test.
- Set explicit upload/body/part limits. Validate file type from content where relevant, generate server-side filenames, and store uploads outside executable/static paths by default.
- Add appropriate security headers at the app or reverse-proxy boundary, including a deliberate Content Security Policy.
- Authorize access to every project/document on every read and write; possession of an object ID is never authorization.
- Return generic public errors and log correlation details server-side. Fail closed on validation and authorization errors.
- Never download or execute untrusted code, change machine-wide settings, or contact external services without explicit user approval.

## Reliability and observability

- Define transaction boundaries in services. A failed operation must not leave a partially saved document.
- Make retries and repeated requests safe where practical. Use idempotency or optimistic concurrency/version checks for document saves rather than silent last-write-wins overwrites.
- Autosave every meaningful edit after a short debounce and show `Unsaved`, `Saving`, `Saved`, or actionable failure state truthfully. Track changes made during an in-flight save so an older response can never falsely mark newer edits as saved.
- Closing an editor dialog, drawer, popover, or plan switch must flush and await its pending save before discarding local state. If saving fails, keep the UI open with the user's input intact and offer retry; never treat closing UI as cancel unless the user explicitly chooses to discard.
- Warn before page navigation while unsaved changes remain, and trigger an immediate save when the page becomes hidden. Debounce is a performance detail, not permission to lose edits.
- Time out external I/O and handle expected failure modes explicitly. Do not catch broad exceptions unless re-raising or translating them at a boundary.
- Provide lightweight health/readiness endpoints when deployment work begins; readiness should verify only dependencies required to serve requests.
- Preserve error causes in logs while presenting stable, non-sensitive messages to clients.

## SQLite storage

- SQLite is the sole persistent data store for the initial application. Keep persistent application data in `data/camdesign.sqlite3`; do not make browser storage, JSON files, or Python objects an alternate source of truth.
- Resolve the database path from a configured project/data root, never from the process's incidental current working directory. Tests must override it with a temporary database.
- Keep `data/` in the repository with a placeholder, but ignore live database files, `-wal` / `-shm` sidecars, backups, exports, and other generated user data. Never commit a populated database.
- Enable SQLite foreign-key enforcement for every connection. Configure a bounded busy timeout, keep write transactions short, and use WAL mode only when compatible with the actual deployment filesystem and backup strategy.
- Access SQLite through the repository/service boundaries. Keep SQLite-specific details out of routes and domain objects so a future storage change remains possible without rewriting the editor.
- Apply schema changes through the adopted migration tool. Migrations and application startup must not delete, recreate, or silently rewrite an existing database.
- Before a destructive migration, create and verify a timestamped backup under `data/backups/` or another explicitly configured `data/` subdirectory. Backups are runtime data and must remain untracked.
- Do not assume SQLite supports multi-host writes. Revisit the storage architecture before horizontal scaling or placing the database on a network filesystem.

## Testing and quality gates

- Add the smallest high-signal test that protects behavior with meaningful regression, security, data-integrity, or domain risk. Every bug fix needs a focused regression test that fails before the fix.
- Do not test Flask, SQLite, browser primitives, static copy, or trivial pass-through code. Do not repeat the same assertion across layers unless each layer has a distinct failure mode.
- CSS-only polish and straightforward template composition do not require automated tests by default; verify them visually at the relevant breakpoints. Prefer a few durable workflow tests over broad low-value coverage.
- Prioritize unit tests for domain geometry, document migrations, validation, commands, and state transitions; use Flask's test client for routes, auth, errors, and persistence integration.
- Test malformed and boundary inputs, authorization failures, CSRF behavior, empty documents, large-but-allowed documents, concurrency/version conflicts, and rollback behavior where relevant.
- Keep tests deterministic: no live network, wall-clock dependence, random values without fixed seeds, or shared mutable databases.
- Use temporary directories/databases and app-factory test configuration. Tests must not read developer secrets or mutate production-like data.
- For UI changes, verify keyboard behavior and responsive layout at desktop and tablet widths. Use browser automation or visual regression only when the repository has adopted the necessary tooling.
- Before declaring work complete, run the narrowest relevant checks and then the repository's full documented gate. Once configured, the expected Python gate is:

```powershell
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

- Run frontend lint/type/test/build commands when they exist. Never claim a check passed unless it was actually run; report skipped or unavailable checks explicitly.
- Do not weaken, delete, skip, or mark tests as expected failures merely to make a gate pass.

## Lean implementation

- Use the fewest clear lines and concepts that deliver the required behavior safely. This is a focus constraint, not permission to omit required UX, validation, security, migrations, or failure handling.
- Do not add an abstraction, configuration option, dependency, compatibility layer, helper, test, or defensive branch without a current requirement or concrete failure mode.
- Prefer direct framework capabilities and a complete vertical slice. Delete superseded code instead of keeping parallel paths, and avoid placeholder implementations that pretend an unfinished feature works.
- Keep reviews small: a change should have one outcome, the necessary implementation, and only the verification that materially increases confidence.

## Dependencies and migrations

- Prefer the standard library, Flask/Werkzeug/Jinja facilities, and existing dependencies.
- Get approval before adding or replacing a runtime dependency, frontend framework, bundler, database, cache, queue, or hosted service. State the need, maintenance cost, license/security implications, and simpler alternatives.
- Keep dependencies direct, minimal, version-constrained, and locked with `uv`. Commit `pyproject.toml` and `uv.lock` changes together.
- A migration must be reviewable, reversible when practical, and safe for existing data. Back up or copy irreplaceable data before destructive transformations.

## Git and commit discipline

- Preserve the user's work. Start with `git status --short`; inspect relevant diffs before editing; never discard or overwrite unrelated changes.
- Do not create a repository, branch, tag, commit, push, merge, rebase, amend, or open a pull request unless the user explicitly asks for that action.
- When asked to commit, make one coherent, reviewable commit for the requested change. Do not mix formatting churn, generated artifacts, dependency upgrades, or unrelated cleanup.
- Before staging, review `git diff --check`, `git diff`, and the relevant test/lint results. Stage only intended paths, then inspect `git diff --cached`.
- Never use `git add -A` in a dirty worktree. Never bypass hooks with `--no-verify`. Never force-push.
- Use an imperative commit subject that describes the outcome, normally at most 72 characters. Add a body when the reason, tradeoff, migration, or verification is not obvious.
- If checks fail, stop and report the failure. Do not commit a known-broken state unless the user explicitly directs it and the commit message clearly records the limitation.
- After a requested commit, report the commit hash, included scope, and checks run. Pushing remains a separate explicit action.

## Agent workflow

### Development server process hygiene

- NEVER leave a development server, watcher, browser-test server, port forward, or child process running after an agent task. This applies on success, failure, interruption, timeout, and tool cancellation.
- Before starting a local server, check the intended port. Do not reuse, replace, or terminate an unexplained listener; identify its owner first and stop only processes the current task started.
- Start temporary servers without an automatic reloader and record the root PID plus any child PIDs. Put cleanup in a `finally`-equivalent path instead of relying on a shell, terminal, or tool session closing.
- Use an isolated temporary data root for UI verification. Remove it only after its entire server process tree has stopped.
- Before the final response, verify every server process started by the task has exited and every port it claimed is no longer listening. If cleanup cannot be verified, do not declare the task complete; report the exact remaining PID and port.

1. Restate the concrete outcome and identify acceptance criteria from the request.
2. Inspect repository instructions, status, relevant code, tests, and configuration.
3. For multi-file or risky work, outline a short plan and keep it updated. Ask only when a choice materially changes product behavior, data safety, architecture, cost, or external state.
4. Implement the smallest complete vertical slice. Keep unrelated refactors out of scope.
5. Add or update tests and documentation alongside the behavior.
6. Run focused checks, then the full available quality gate. Review the final diff for accidental files, secrets, debug code, and scope creep.
7. Summarize the outcome, files changed, verification performed, and any remaining risks or follow-ups. Do not hide uncertainty or unverified assumptions.

## Stop conditions

Stop and ask before proceeding if work would:

- destroy or irreversibly migrate user data;
- overwrite unexplained local changes;
- expose the app publicly, deploy, incur cost, or send data to an external service;
- change authentication/authorization policy or the canonical document format without clear acceptance criteria;
- require secrets or production access that were not provided;
- introduce a major dependency or architecture outside the requested scope.

## Definition of done

A change is done only when it satisfies the request, respects the architecture and security boundaries above, includes appropriate tests, passes all available relevant checks, contains no unrelated changes or secrets, leaves no agent-started processes or listeners running, and is documented well enough for the next contributor to understand. A prototype shortcut must be labeled, scoped, and tracked rather than silently becoming production design.
