function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? "";
}

async function parseJson(response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error("The server returned an unexpected response.");
  }
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error?.message ?? "The request failed.");
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
