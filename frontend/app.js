const statusEl = document.querySelector("#status");
const scanButton = document.querySelector("#scanButton");
const loginPanel = document.querySelector("#loginPanel");
const appShell = document.querySelector("#appShell");
const loginButton = document.querySelector("#loginButton");
const resumeButton = document.querySelector("#resumeButton");
const logoutButton = document.querySelector("#logoutButton");
const backupLink = document.querySelector("#backupLink");
const adminToolbox = document.querySelector("#adminToolbox");
const nextcloudUrl = document.querySelector("#nextcloudUrl");
const userBadge = document.querySelector("#userBadge");
const applyFilters = document.querySelector("#applyFilters");
const adminReportButton = document.querySelector("#adminReportButton");
const closeReportButton = document.querySelector("#closeReportButton");
const adminReportPanel = document.querySelector("#adminReportPanel");
const adminReportContent = document.querySelector("#adminReportContent");
const backupFile = document.querySelector("#backupFile");
const confirmImport = document.querySelector("#confirmImport");
const importBackupButton = document.querySelector("#importBackupButton");
let map;
let cluster;
let currentUser;
let loginWindow;
let activeFlowId;

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function popupHtml(photo) {
  const takenAt = photo.taken_at ? new Date(photo.taken_at).toLocaleString("it-IT") : "Data non disponibile";
  const thumb = photo.thumbnail_url ? `<img src="${photo.thumbnail_url}" alt="">` : "";
  const link = photo.nextcloud_url ? `<a href="${photo.nextcloud_url}" target="_blank" rel="noreferrer">Apri in Nextcloud</a>` : "";
  return `
    <article class="popup">
      ${thumb}
      <strong>${photo.filename}</strong>
      <span>${takenAt}</span>
      ${link}
    </article>
  `;
}

async function loadPhotos() {
  const params = new URLSearchParams();
  const fromDate = document.querySelector("#fromDate").value;
  const toDate = document.querySelector("#toDate").value;
  const folder = document.querySelector("#folder").value.trim();
  if (fromDate) params.set("from_date", fromDate);
  if (toDate) params.set("to_date", toDate);
  if (folder) params.set("folder", folder);
  params.set("limit", "10000");

  const photos = await fetchJson(`/api/photos/map?${params.toString()}`);
  cluster.clearLayers();
  photos.forEach((photo) => {
    const marker = L.marker([photo.latitude, photo.longitude]);
    marker.bindPopup(popupHtml(photo), { maxWidth: 280 });
    cluster.addLayer(marker);
  });
  if (photos.length) {
    map.fitBounds(cluster.getBounds(), { padding: [24, 24], maxZoom: 15 });
  }
  statusEl.textContent = `${photos.length} foto geolocalizzate`;
}

async function init() {
  const config = await fetchJson("/api/config");
  if (config.nextcloudUrl) {
    nextcloudUrl.value = config.nextcloudUrl;
  }
  try {
    currentUser = await fetchJson("/api/auth/me");
  } catch {
    showLogin();
    return;
  }
  showApp();
  await initMap(config);
}

async function initMap(config) {
  if (map) {
    await loadPhotos();
    return;
  }
  map = L.map("map", { zoomControl: true }).setView(
    [config.defaultLat, config.defaultLon],
    config.defaultZoom
  );
  L.tileLayer(config.tileUrl, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  cluster = L.markerClusterGroup();
  map.addLayer(cluster);
  await loadPhotos();
}

function showLogin() {
  loginPanel.hidden = false;
  loginPanel.style.display = "grid";
  appShell.hidden = true;
  appShell.style.display = "none";
  scanButton.hidden = true;
  logoutButton.hidden = true;
  backupLink.hidden = true;
  adminToolbox.hidden = true;
  userBadge.hidden = true;
  adminReportPanel.hidden = true;
  statusEl.textContent = "Accesso richiesto";
}

function showApp() {
  loginPanel.hidden = true;
  loginPanel.style.display = "none";
  appShell.hidden = false;
  appShell.style.display = "grid";
  scanButton.hidden = false;
  logoutButton.hidden = false;
  backupLink.hidden = currentUser.role !== "admin";
  adminToolbox.hidden = currentUser.role !== "admin";
  adminReportPanel.hidden = true;
  userBadge.hidden = false;
  userBadge.textContent = currentUser.displayName || currentUser.loginName;
  statusEl.textContent = "Caricamento foto...";
}

async function pollLogin(flowId) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 10 * 60 * 1000) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const result = await fetchJson("/api/auth/nextcloud/poll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ flow_id: flowId }),
    });
    if (result.status === "authenticated") {
      await enterApp(result.user);
      return;
    }
  }
  throw new Error("Tempo di login scaduto");
}

async function enterApp(user) {
  currentUser = user;
  activeFlowId = null;
  resumeButton.hidden = true;
  if (loginWindow && !loginWindow.closed) {
    loginWindow.close();
  }
  window.focus();
  showApp();
  const config = await fetchJson("/api/config");
  await initMap(config);
}

loginButton.addEventListener("click", async () => {
  loginButton.disabled = true;
  statusEl.textContent = "Apro il login Nextcloud...";
  try {
    const payload = {};
    if (nextcloudUrl.value.trim()) payload.nextcloud_url = nextcloudUrl.value.trim();
    const flow = await fetchJson("/api/auth/nextcloud/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    activeFlowId = flow.flowId;
    loginWindow = window.open(flow.loginUrl, "_blank");
    resumeButton.hidden = false;
    statusEl.textContent = "Completa il login nella finestra Nextcloud, poi torna qui.";
    await pollLogin(flow.flowId);
  } catch (error) {
    statusEl.textContent = `Errore login: ${error.message}`;
  } finally {
    loginButton.disabled = false;
  }
});

resumeButton.addEventListener("click", async () => {
  try {
    if (activeFlowId) {
      const result = await fetchJson("/api/auth/nextcloud/poll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flow_id: activeFlowId }),
      });
      if (result.status === "authenticated") {
        await enterApp(result.user);
        return;
      }
    }
    currentUser = await fetchJson("/api/auth/me");
    await enterApp(currentUser);
  } catch (error) {
    statusEl.textContent = `Autorizzazione non ancora completata: ${error.message}`;
  }
});

logoutButton.addEventListener("click", async () => {
  await fetchJson("/api/auth/logout", { method: "POST" });
  currentUser = null;
  showLogin();
});

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  statusEl.textContent = "Scansione avviata...";
  try {
    await fetchJson("/api/admin/scan", { method: "POST" });
    statusEl.textContent = "Scansione in esecuzione. Aggiorna tra poco.";
    if (!adminReportPanel.hidden) {
      await loadAdminReport();
    }
  } catch (error) {
    statusEl.textContent = `Errore scansione: ${error.message}`;
  } finally {
    scanButton.disabled = false;
  }
});

adminReportButton.addEventListener("click", async () => {
  adminReportPanel.hidden = false;
  adminReportPanel.style.display = "grid";
  adminReportContent.innerHTML = `<p>Caricamento report...</p>`;
  try {
    await loadAdminReport();
  } catch (error) {
    adminReportContent.innerHTML = `<p>Errore report: ${escapeHtml(error.message)}</p>`;
  }
});

closeReportButton.addEventListener("click", () => {
  adminReportPanel.hidden = true;
  adminReportPanel.style.display = "none";
});

async function loadAdminReport() {
  const report = await fetchJson("/api/admin/report");
  adminReportContent.innerHTML = reportHtml(report);
}

function reportHtml(report) {
  return `
    <section class="report-section">
      <h3>Utenti registrati</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Utente</th>
              <th>Ruolo</th>
              <th>Foto</th>
              <th>GPS</th>
              <th>Ultimo login</th>
              <th>Ultimo indice</th>
            </tr>
          </thead>
          <tbody>
            ${report.users.map(userRowHtml).join("") || `<tr><td colspan="6">Nessun utente</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
    <section class="report-section">
      <h3>Scansioni in corso</h3>
      ${jobsTable(report.runningJobs, true)}
    </section>
    <section class="report-section">
      <h3>Ultime scansioni</h3>
      ${jobsTable(report.recentJobs, false)}
    </section>
  `;
}

function userRowHtml(user) {
  return `
    <tr>
      <td>
        <strong>${escapeHtml(user.display_name || user.nextcloud_login_name)}</strong>
        <span>${escapeHtml(user.nextcloud_server_url || "")}</span>
      </td>
      <td>${escapeHtml(user.role)}${user.disabled ? " / disabilitato" : ""}</td>
      <td>${Number(user.photos_total || 0)}</td>
      <td>${Number(user.photos_with_gps || 0)}</td>
      <td>${formatDate(user.last_login_at)}</td>
      <td>${formatDate(user.last_indexed_at)}</td>
    </tr>
  `;
}

function jobsTable(jobs, runningOnly) {
  if (!jobs.length) {
    return `<p>${runningOnly ? "Nessuna scansione in corso" : "Nessuna scansione registrata"}</p>`;
  }
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Utente</th>
            <th>Stato</th>
            <th>Progresso</th>
            <th>GPS</th>
            <th>Errori EXIF</th>
            <th>Avvio</th>
          </tr>
        </thead>
        <tbody>
          ${jobs.map(jobRowHtml).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function jobRowHtml(job) {
  const total = Number(job.total_files || 0);
  const processed = Number(job.processed_files || 0);
  const progress = total ? `${processed}/${total}` : `${processed}`;
  return `
    <tr>
      <td>${escapeHtml(job.nextcloud_login_name)}</td>
      <td>${escapeHtml(job.status)}</td>
      <td>${progress}</td>
      <td>${Number(job.with_gps || 0)}</td>
      <td>${Number(job.exif_errors || 0)}</td>
      <td>${formatDate(job.started_at)}</td>
    </tr>
  `;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString("it-IT") : "-";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

applyFilters.addEventListener("click", () => {
  loadPhotos().catch((error) => {
    statusEl.textContent = `Errore caricamento: ${error.message}`;
  });
});

importBackupButton.addEventListener("click", async () => {
  const file = backupFile.files[0];
  if (!file) {
    statusEl.textContent = "Seleziona un file backup JSON.";
    return;
  }
  if (!confirmImport.checked) {
    statusEl.textContent = "Conferma la sostituzione dei dati prima di importare.";
    return;
  }

  importBackupButton.disabled = true;
  statusEl.textContent = "Import backup in corso...";
  const formData = new FormData();
  formData.append("backup", file);
  try {
    const result = await fetchJson("/api/admin/backup/import?confirm=IMPORT", {
      method: "POST",
      body: formData,
    });
    statusEl.textContent = `Import completato: ${result.photos} foto caricate`;
    confirmImport.checked = false;
    backupFile.value = "";
    await loadPhotos();
  } catch (error) {
    statusEl.textContent = `Errore import: ${error.message}`;
  } finally {
    importBackupButton.disabled = false;
  }
});

init().catch((error) => {
  statusEl.textContent = `Errore avvio: ${error.message}`;
});
