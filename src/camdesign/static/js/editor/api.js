function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? "";
}

function requestError(message, response, payload) {
  const error = new Error(message);
  error.status = response.status;
  error.payload = payload;
  return error;
}

async function parseJson(response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw requestError("The server returned an unexpected response.", response, null);
  }
  const payload = await response.json();
  if (!response.ok) {
    throw requestError(payload.error?.message ?? "The request failed.", response, payload);
  }
  return payload;
}

export async function loadProject(url, signal) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });
  return parseJson(response);
}

export async function loadCatalog(url, signal) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });
  return parseJson(response);
}

// The server names the file, since it is the side that knows the project. Werkzeug
// quotes the name only when it has to, and appends a UTF-8 copy we can ignore.
function filenameFrom(disposition) {
  return /filename="?([^";]+)"?/.exec(disposition)?.[1]?.trim() ?? "bom.pdf";
}

// Fetched rather than followed as a link: a failed export must land in the status line
// beside the save state, not replace the plan the estimator is standing in front of
// with an error page, or save that page to disk under a .pdf name.
export async function fetchExport(url, signal) {
  const response = await fetch(url, { headers: { Accept: "application/pdf" }, signal });
  if (!response.ok || !(response.headers.get("content-type") ?? "").includes("application/pdf")) {
    throw requestError(
      response.status === 404
        ? "This plan is no longer on the server."
        : "The PDF could not be generated. Try again.",
      response,
      null,
    );
  }
  return {
    blob: await response.blob(),
    filename: filenameFrom(response.headers.get("content-disposition") ?? ""),
  };
}

export async function saveProject(url, payload, signal) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken(),
    },
    body: JSON.stringify(payload),
    signal,
  });
  return parseJson(response);
}
