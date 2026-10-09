// Escape a value for safe insertion into HTML text or a quoted attribute.
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Encode a value as a JS literal for use inside an inline handler attribute,
// e.g. onclick="fn(${jsArg(name)})" -- note: no surrounding quotes in the template.
function jsArg(value) {
  return escapeHtml(JSON.stringify(value ?? null));
}

// Error thrown by requestJson. status is 0 for network failures; message is
// null when the server gave no error text.
class ApiError extends Error {
  constructor(message, status) {
    super();
    this.message = message;
    this.name = 'ApiError';
    this.status = status;
  }
}

// fetch + JSON parse. Throws ApiError on network failure (status 0, message null)
// or when the response is not ok / contains an `error` field.
async function requestJson(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (e) {
    throw new ApiError(null, 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) {
    throw new ApiError(data.error || data.detail || null, res.status);
  }
  return data;
}
