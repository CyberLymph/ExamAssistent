(function () {
  const params = new URLSearchParams(window.location.search);
  const chat_id = params.get("chat_id");
  const run_id = params.get("run_id");

  const loading = document.getElementById("loading");
  const progressBar = document.getElementById("progressBar");
  const meta = document.getElementById("meta");
  const simScoreEl = document.getElementById("simScore");
  const readLevelEl = document.getElementById("readLevel");

  const pager = document.getElementById("pager");
  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");
  const pageNowEl = document.getElementById("pageNow");
  const pageMaxEl = document.getElementById("pageMax");

  const grid = document.getElementById("grid");
  const colML = document.getElementById("colML");
  const colSL = document.getElementById("colSL");
  const endMsg = document.getElementById("endMsg");

  // Einstellungen
  const PAGE_SIZE = 3; // 3 Aufgabenpaare pro Seite

  // Zustand
  let tasks = [];
  let page = 1;
  let pageMax = 1;

  function setProgress(pct) {
    if (progressBar) progressBar.style.width = pct;
  }

  function chunk(arr, size) {
    const out = [];
    for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
    return out;
  }

  function fmtPercent(v) {
    if (typeof v !== "number") return "–";
    return (v * 100).toFixed(1) + " %";
  }

  function renderPage() {
    // Seiteninfo
    pageMaxEl.textContent = pageMax;
    pageNowEl.textContent = page;

    // Buttons aktivieren/deaktivieren
    btnPrev.disabled = page <= 1;
    btnNext.disabled = page >= pageMax;

    // Inhalte
    colML.innerHTML = "";
    colSL.innerHTML = "";

    const groups = chunk(tasks, PAGE_SIZE);
    const slice = groups[page - 1] || [];

    slice.forEach((t) => {
      // linke Spalte (ML)
      const ml = document.createElement("div");
      ml.className = "mb-3 p-2 border rounded bg-white";
      ml.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
          <b>${t.task_id}</b>
          <span class="badge bg-secondary">${fmtPercent(t.similarity)}</span>
        </div>
        <div class="mt-2"><pre class="m-0" style="white-space:pre-wrap">${t.model_solution || "(Keine ML verfügbar)"}</pre></div>
      `;
      colML.appendChild(ml);

      // rechte Spalte (SL + Feedback)
      const sl = document.createElement("div");
      sl.className = "mb-3 p-2 border rounded bg-white";
      sl.innerHTML = `
        <b>${t.task_id}</b>
        <div class="mt-2"><u>Studentenlösung:</u></div>
        <pre class="m-0" style="white-space:pre-wrap">${t.student_answer || "(Keine SL verfügbar)"}</pre>
        <div class="mt-2"><u>Feedback (detaillierter Vergleich):</u></div>
        <pre class="m-0" style="white-space:pre-wrap">${t.feedback || "(Kein Feedback)"}</pre>
      `;
      colSL.appendChild(sl);
    });

    // Ende-Hinweis
    endMsg.classList.toggle("d-none", page < pageMax);
  }

  async function init() {
    try {
      setProgress("90%");
      const res = await fetch(`http://127.0.0.1:8000/detailed-analysis?chat_id=${encodeURIComponent(chat_id)}&run_id=${encodeURIComponent(run_id)}`);

      const data = await res.json();
      if (!res.ok || !data?.summary) throw new Error(data?.detail || "Analyse konnte nicht geladen werden.");

      const s = data.summary;
      tasks = Array.isArray(s.tasks) ? s.tasks : [];
      if (tasks.length === 0) throw new Error("Keine Aufgaben gefunden.");

      // Meta
      simScoreEl.textContent = fmtPercent(s.similarity_score);
      readLevelEl.textContent = s.readability_metrics?.lesbarkeitsgrad || "–";

      // Anzeige
      loading.classList.add("d-none");
      meta.classList.remove("d-none");
      grid.classList.remove("d-none");
      pager.classList.remove("d-none");

      // Pagination
      pageMax = Math.max(1, Math.ceil(tasks.length / PAGE_SIZE));
      page = 1;
      renderPage();
      setProgress("100%");
    } catch (e) {
      loading.textContent = "❌ Fehler: " + e.message;
    }
  }

  // Pager
  btnPrev?.addEventListener("click", () => {
    if (page > 1) {
      page -= 1;
      renderPage();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
  btnNext?.addEventListener("click", () => {
    if (page < pageMax) {
      page += 1;
      renderPage();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  // Start
  init();
})();
