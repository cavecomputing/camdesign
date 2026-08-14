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
