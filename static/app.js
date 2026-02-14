const grid = document.getElementById("keg-grid");
const board = document.getElementById("keg-board");
const syncBtn = document.getElementById("sync-btn");
const overlay = document.getElementById("modal-overlay");
const form = document.getElementById("keg-form");
const cancelBtn = document.getElementById("modal-cancel");
const closeBtn = document.getElementById("modal-close");
const batchInfoPanel = document.getElementById("batch-info-panel");
const batchInfoNotes = document.getElementById("batch-info-notes");

let kegs = [];
let batches = [];
let currentView = "grid";

const LOCATIONS = ["At Brewery", "Conditioning Fridge", "Michael", "Troy", "Brent"];

// ── API helpers ──────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function loadKegs() {
  kegs = await api("GET", "/api/kegs");
  render();
}

async function loadBatches() {
  batches = await api("GET", "/api/batches");
}

function render() {
  if (currentView === "grid") {
    renderGrid();
  } else {
    renderBoard();
  }
}

// ── View Toggle ──────────────────────────────────────────────

document.querySelectorAll(".view-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    if (view === currentView) return;
    currentView = view;

    document.querySelectorAll(".view-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    if (view === "grid") {
      grid.classList.remove("hidden");
      board.classList.add("hidden");
    } else {
      grid.classList.add("hidden");
      board.classList.remove("hidden");
    }
    render();
  });
});

// ── Shared card content builder ──────────────────────────────

function buildCardContent(keg, { showLocation = true } = {}) {
  const statusClass = `badge-${keg.status}`;
  const statusLabel = keg.status.replace("_", " ");

  let bodyContent = "";
  if (keg.batch) {
    const abv = keg.batch.abv != null ? `${keg.batch.abv.toFixed(1)}%` : "";
    const batchLabel = keg.batch.batch_no ? `#${keg.batch.batch_no} ` : "";
    const displayName = keg.batch.recipe_name || keg.batch.name;

    bodyContent = `
      <div class="keg-batch-name">${batchLabel}${esc(displayName)}</div>
      <div class="keg-style">${esc(keg.batch.style)}${abv ? " &middot; " + abv : ""}</div>
      <div class="keg-meta">
    `;

    if (keg.batch.bottling_date) {
      bodyContent += `<div class="keg-detail"><span class="detail-icon">&#9641;</span> Bottled ${esc(keg.batch.bottling_date)}</div>`;
    }
    if (showLocation && keg.location) {
      bodyContent += `<div class="keg-detail"><span class="detail-icon">&#9673;</span> ${esc(keg.location)}</div>`;
    }
    if (keg.batch.batch_notes) {
      bodyContent += `<div class="keg-notes-preview">${esc(keg.batch.batch_notes)}</div>`;
    }

    bodyContent += `</div>`;
  } else {
    bodyContent = `<div class="keg-empty-msg">No batch assigned</div>`;
    if (showLocation && keg.location) {
      bodyContent += `<div class="keg-detail"><span class="detail-icon">&#9673;</span> ${esc(keg.location)}</div>`;
    }
  }

  return `
    <div class="keg-header">
      <span class="keg-number">${esc(keg.label)}</span>
      <span class="keg-status-badge ${statusClass}">${statusLabel}</span>
    </div>
    ${bodyContent}
  `;
}

// ── Grid View ────────────────────────────────────────────────

function renderGrid() {
  grid.innerHTML = "";
  for (const keg of kegs) {
    const card = document.createElement("div");
    card.className = "keg-card";

    card.innerHTML = `
      <div class="keg-card-body" data-keg-id="${keg.id}">
        ${buildCardContent(keg)}
      </div>
      <div class="keg-card-footer">
        <button class="keg-reset-btn" data-reset-id="${keg.id}">Reset Keg</button>
      </div>
    `;

    card.querySelector(".keg-card-body").addEventListener("click", () => openModal(keg));

    card.querySelector(".keg-reset-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Reset ${keg.label} to empty? This will clear the batch, location, and notes.`)) return;
      await api("POST", `/api/kegs/${keg.id}/reset`);
      await loadKegs();
    });

    grid.appendChild(card);
  }
}

// ── Board View ───────────────────────────────────────────────

function getKegColumn(keg) {
  if (!keg.location) return "At Brewery";
  return keg.location;
}

function renderBoard() {
  board.innerHTML = "";

  for (const loc of LOCATIONS) {
    const col = document.createElement("div");
    col.className = "board-column";

    const columnKegs = kegs.filter((k) => getKegColumn(k) === loc);

    col.innerHTML = `
      <div class="board-column-header">
        <span class="board-column-title">${esc(loc)}</span>
        <span class="board-column-count">${columnKegs.length}</span>
      </div>
    `;

    const body = document.createElement("div");
    body.className = "board-column-body";
    body.dataset.location = loc;

    // Drop zone events
    body.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      body.classList.add("drag-over");
    });

    body.addEventListener("dragleave", (e) => {
      if (!body.contains(e.relatedTarget)) {
        body.classList.remove("drag-over");
      }
    });

    body.addEventListener("drop", async (e) => {
      e.preventDefault();
      body.classList.remove("drag-over");
      const kegId = e.dataTransfer.getData("text/plain");
      const newLocation = loc === "At Brewery" ? "" : loc;

      await api("PUT", `/api/kegs/${kegId}`, { location: newLocation });
      await loadKegs();
    });

    for (const keg of columnKegs) {
      const card = document.createElement("div");
      card.className = "board-card";
      card.draggable = true;
      card.dataset.kegId = keg.id;

      const cardBody = document.createElement("div");
      cardBody.className = "board-card-body";
      cardBody.innerHTML = buildCardContent(keg, { showLocation: false });

      const cardFooter = document.createElement("div");
      cardFooter.className = "keg-card-footer";
      cardFooter.innerHTML = `<button class="keg-reset-btn">Reset Keg</button>`;
      cardFooter.querySelector(".keg-reset-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Reset ${keg.label} to empty? This will clear the batch, location, and notes.`)) return;
        await api("POST", `/api/kegs/${keg.id}/reset`);
        await loadKegs();
      });

      card.appendChild(cardBody);
      card.appendChild(cardFooter);

      // Drag events
      card.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", keg.id);
        e.dataTransfer.effectAllowed = "move";
        requestAnimationFrame(() => card.classList.add("dragging"));
      });

      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
      });

      // Click card body to edit
      cardBody.addEventListener("click", (e) => {
        if (e.defaultPrevented) return;
        openModal(keg);
      });

      body.appendChild(card);
    }

    col.appendChild(body);
    board.appendChild(col);
  }
}

// ── Helpers ──────────────────────────────────────────────────

function esc(str) {
  const el = document.createElement("span");
  el.textContent = str || "";
  return el.innerHTML;
}

// ── Modal ────────────────────────────────────────────────────

function openModal(keg) {
  document.getElementById("modal-title").textContent = keg.label;
  document.getElementById("keg-id").value = keg.id;
  document.getElementById("keg-label").value = keg.label;
  document.getElementById("keg-status").value = keg.status;
  document.getElementById("keg-location").value = keg.location || "";
  document.getElementById("keg-date-purchased").value = keg.date_purchased || "";
  document.getElementById("keg-notes").value = keg.notes || "";

  // Show batch notes if batch is assigned
  if (keg.batch && keg.batch.batch_notes) {
    batchInfoNotes.textContent = keg.batch.batch_notes;
    batchInfoPanel.classList.remove("hidden");
  } else {
    batchInfoPanel.classList.add("hidden");
  }

  // Populate batch dropdown
  const batchSelect = document.getElementById("keg-batch");
  batchSelect.innerHTML = `<option value="">-- None --</option>`;
  for (const b of batches) {
    const opt = document.createElement("option");
    opt.value = b.id;
    const prefix = b.batch_no ? `#${b.batch_no} ` : "";
    opt.textContent = `${prefix}${b.recipe_name || b.name} (${b.style || "no style"})`;
    if (keg.batch_id === b.id) opt.selected = true;
    batchSelect.appendChild(opt);
  }

  // Update batch notes panel when batch selection changes
  batchSelect.onchange = () => {
    const selected = batches.find((b) => b.id === batchSelect.value);
    if (selected && selected.batch_notes) {
      batchInfoNotes.textContent = selected.batch_notes;
      batchInfoPanel.classList.remove("hidden");
    } else {
      batchInfoPanel.classList.add("hidden");
    }
  };

  overlay.classList.remove("hidden");
}

function closeModal() {
  overlay.classList.add("hidden");
}

cancelBtn.addEventListener("click", closeModal);
closeBtn.addEventListener("click", closeModal);
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeModal();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("keg-id").value;
  const batchVal = document.getElementById("keg-batch").value;

  const payload = {
    label: document.getElementById("keg-label").value,
    status: document.getElementById("keg-status").value,
    location: document.getElementById("keg-location").value,
    date_purchased: document.getElementById("keg-date-purchased").value,
    notes: document.getElementById("keg-notes").value,
  };

  if (batchVal) {
    payload.batch_id = batchVal;
  } else {
    payload.clear_batch = true;
  }

  await api("PUT", `/api/kegs/${id}`, payload);
  closeModal();
  await loadKegs();
});

// ── Sync ─────────────────────────────────────────────────────

syncBtn.addEventListener("click", async () => {
  if (syncBtn.classList.contains("syncing")) return;
  syncBtn.classList.add("syncing");
  syncBtn.innerHTML = `
    <svg class="sync-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14.5 3.5A8 8 0 0 1 18 10h-3l4 4 4-4h-3a10 10 0 0 0-5.5-8.5" transform="scale(0.8) translate(2,2)"/>
      <path d="M5.5 16.5A8 8 0 0 1 2 10h3L1 6l-4 4h3a10 10 0 0 0 5.5 8.5" transform="scale(0.8) translate(4,2)"/>
    </svg>
    Syncing&hellip;
  `;
  try {
    const result = await api("POST", "/api/batches/sync");
    syncBtn.textContent = `Synced ${result.synced} batches`;
    await loadBatches();
    await loadKegs();
  } catch (err) {
    syncBtn.textContent = "Sync failed!";
    console.error(err);
  }
  setTimeout(() => {
    syncBtn.innerHTML = `
      <svg class="sync-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14.5 3.5A8 8 0 0 1 18 10h-3l4 4 4-4h-3a10 10 0 0 0-5.5-8.5" transform="scale(0.8) translate(2,2)"/>
        <path d="M5.5 16.5A8 8 0 0 1 2 10h3L1 6l-4 4h3a10 10 0 0 0 5.5 8.5" transform="scale(0.8) translate(4,2)"/>
      </svg>
      Sync from Brewfather
    `;
    syncBtn.classList.remove("syncing");
  }, 2000);
});

// ── Init ─────────────────────────────────────────────────────

(async () => {
  await loadBatches();
  await loadKegs();
})();
