const statusEl = document.querySelector("#status");
const scanButton = document.querySelector("#scanButton");
const applyFilters = document.querySelector("#applyFilters");
let map;
let cluster;

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
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

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  statusEl.textContent = "Scansione avviata...";
  try {
    await fetchJson("/api/admin/scan", { method: "POST" });
    statusEl.textContent = "Scansione in esecuzione. Aggiorna tra poco.";
  } catch (error) {
    statusEl.textContent = `Errore scansione: ${error.message}`;
  } finally {
    scanButton.disabled = false;
  }
});

applyFilters.addEventListener("click", () => {
  loadPhotos().catch((error) => {
    statusEl.textContent = `Errore caricamento: ${error.message}`;
  });
});

init().catch((error) => {
  statusEl.textContent = `Errore avvio: ${error.message}`;
});
