const $ = (id) => document.getElementById(id);
const logEl = $("log");
let catalog = [];
let lastRequestId = "";

function log(title, payload) {
  const ts = new Date().toISOString();
  const body = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  logEl.textContent = `[${ts}] ${title}\n${body}`;
}

function creds() {
  return {
    base_url: $("baseUrl").value.trim(),
    username: $("username").value.trim(),
    password: $("password").value,
  };
}

function currentObject() {
  return catalog.find((o) => o.key === $("objectKey").value);
}

function renderObject() {
  const obj = currentObject();
  if (!obj) return;
  $("objectMeta").textContent =
    `${obj.module} · UCM ${obj.ucm_account_ui} · tables ${obj.interface_tables.join(", ")} · import ${obj.import_job_display}`;
  $("objectNotes").innerHTML = (obj.notes || []).map((n) => `<li>${n}</li>`).join("");
  $("interfaceId").value = obj.interface_id || "";
  const defaults = (obj.import_parameters || []).map((p) => p.default ?? "#NULL");
  $("importParams").value = defaults.join(",");
  $("paramHint").textContent =
    "Order: " + (obj.import_parameters || []).map((p) => p.label).join(" → ");
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { detail: text }; }
  if (!res.ok) {
    const detail = data.detail || data.message || text;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

async function boot() {
  const [objects, defaults] = await Promise.all([
    api("/api/objects"),
    api("/api/defaults"),
  ]);
  catalog = objects;
  $("objectKey").innerHTML = objects
    .map((o) => `<option value="${o.key}">${o.label}</option>`)
    .join("");
  if (defaults.base_url) $("baseUrl").value = defaults.base_url;
  if (defaults.username) $("username").value = defaults.username;
  renderObject();
}

$("objectKey").addEventListener("change", renderObject);

$("file").addEventListener("change", () => {
  const file = $("file").files[0];
  if (!file) {
    $("fileChosen").textContent = "No file chosen yet. In the XLSM click Generate CSV File, save the ZIP, then choose it here.";
    return;
  }
  const ok = file.name.toLowerCase().endsWith(".zip");
  $("fileChosen").textContent = ok
    ? `Selected: ${file.name} (${Math.ceil(file.size / 1024)} KB)`
    : `Selected ${file.name} — this must be a .zip from Generate CSV File, not the XLSM.`;
});

$("pingBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/ping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(creds()),
    });
    log("Connection OK", data);
  } catch (err) {
    log("Connection failed", err.message);
  }
});

$("lookupBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/lookup-interface", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...creds(), object_key: $("objectKey").value }),
    });
    log("inboundProcessDetails", data);
    const blob = JSON.stringify(data);
    const match = blob.match(/"InterfaceId"\s*:\s*"(\d+)"/i);
    if (match) {
      $("interfaceId").value = match[1];
      log("inboundProcessDetails — Interface ID copied", match[1]);
    }
  } catch (err) {
    log("Lookup failed", err.message);
  }
});

$("loadBtn").addEventListener("click", async () => {
  const file = $("file").files[0];
  if (!file) {
    log("Missing file", "Choose the ZIP produced by Generate CSV File on the FBDI template.");
    return;
  }
  const mode = document.querySelector("input[name=mode]:checked").value;
  const form = new FormData();
  const c = creds();
  form.append("base_url", c.base_url);
  form.append("username", c.username);
  form.append("password", c.password);
  form.append("object_key", $("objectKey").value);
  form.append("mode", mode);
  form.append("interface_id", $("interfaceId").value.trim());
  form.append("run_import", $("runImport").checked ? "Y" : "N");
  form.append("wait_for_load", $("waitForLoad").checked ? "Y" : "N");
  form.append("wait_seconds", $("waitSeconds").value.trim() || "300");
  form.append("import_parameters", $("importParams").value.trim());
  form.append("file", file);

  $("loadBtn").disabled = true;
  log("Submitting", { file: file.name, mode, object: $("objectKey").value });
  try {
    const data = await api("/api/load", { method: "POST", body: form });
    const ids = [];
    for (const step of data.steps || []) {
      if (step.request_id) ids.push(`${step.name}=${step.request_id}`);
      if (step.document_id) ids.push(`UCM DocumentId=${step.document_id}`);
    }
    lastRequestId = data.import_request_id || data.load_request_id || "";
    if (lastRequestId) $("statusRequestId").value = lastRequestId;
    $("lastIds").textContent = ids.join(" · ") || "Submitted";
    log("Load finished", data);
  } catch (err) {
    log("Load failed", err.message);
  } finally {
    $("loadBtn").disabled = false;
  }
});

$("statusBtn").addEventListener("click", async () => {
  const requestId = $("statusRequestId").value.trim() || lastRequestId || prompt("ESS Request ID");
  if (!requestId) return;
  try {
    const data = await api("/api/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...creds(), request_id: requestId }),
    });
    lastRequestId = requestId;
    $("statusRequestId").value = requestId;
    log(`ESS status for ${requestId}`, data);
  } catch (err) {
    log("Status failed", err.message);
  }
});

$("logBtn").addEventListener("click", async () => {
  const requestId = $("statusRequestId").value.trim() || lastRequestId || prompt("ESS Request ID");
  if (!requestId) return;
  try {
    const data = await api("/api/job-details", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...creds(), request_id: requestId }),
    });
    lastRequestId = requestId;
    $("statusRequestId").value = requestId;
    log(`ESS log for ${requestId}`, data);
  } catch (err) {
    log("Log download failed", err.message);
  }
});

boot().catch((err) => log("UI failed to start", err.message));
