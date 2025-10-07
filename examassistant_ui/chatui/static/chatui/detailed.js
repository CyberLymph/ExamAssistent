(async function () {
  // ===============================
  // Parameter aus URL lesen
  // ===============================
  const params = new URLSearchParams(window.location.search);
  const chat_id = params.get("chat_id");
  const run_id = params.get("run_id");

  const loading = document.getElementById("loading");
  const container = document.getElementById("analysis");

  // ===============================
  // Helper
  // ===============================
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html) e.innerHTML = html;
    return e;
  }

  // ===============================
  // Analyse laden
  // ===============================
  try {
    const res = await fetch(`/api/detailed-analysis?chat_id=${chat_id}&run_id=${run_id}`);
    if (!res.ok) throw new Error("Analyse konnte nicht geladen werden.");
    const data = await res.json();
    const s = data.summary;

    loading.classList.add("hidden");
    container.classList.remove("hidden");

    // ===============================
    // Header
    // ===============================
    const header = el("div", "p-4 border-b mb-4", `
      <h2>🧠 Detaillierte Analyse</h2>
      <p><b>Chat-ID:</b> ${chat_id} | <b>Run-ID:</b> ${run_id}</p>
      <p><b>Gesamtähnlichkeit:</b> ${(s.similarity_score * 100).toFixed(2)}%</p>
    `);
    container.appendChild(header);

    // ===============================
    // Bloom-Taxonomie Info
    // ===============================
    const bloomInfo = el("div", "bg-gray-50 p-3 rounded mb-4");
    bloomInfo.innerHTML = `
      <h3>🌱 Bloom-Taxonomie</h3>
      <p>Ein Klassifikationssystem für Lernziele, das hilft, Aufgaben und Materialien auf verschiedene kognitive Niveaus abzustimmen.</p>
      <ol>
        <li><b>Erinnern</b> – Fakten wiedergeben („Definieren Sie ...“)</li>
        <li><b>Verstehen</b> – Konzepte erklären („Beschreiben Sie ...“)</li>
        <li><b>Anwenden</b> – Wissen in neuen Situationen nutzen („Lösen Sie ...“)</li>
        <li><b>Analysieren</b> – Strukturen und Zusammenhänge erkennen („Vergleichen Sie ...“)</li>
        <li><b>Bewerten</b> – Urteile fällen, Kriterien anwenden („Beurteilen Sie ...“)</li>
        <li><b>Erschaffen</b> – Neues entwickeln („Entwerfen Sie ...“)</li>
      </ol>
    `;
    container.appendChild(bloomInfo);

    // ===============================
    // Lesbarkeitsinfo
    // ===============================
    const readInfo = el("div", "bg-blue-50 p-3 rounded mb-4");
    const r = s.readability_metrics || {};
    readInfo.innerHTML = `
      <h3>📖 Flesch Reading Ease (Lesbarkeitsindex)</h3>
      <p>Ein Maß für die Verständlichkeit von Texten (Deutsch: 180 – ASL – (58,5 × ASW))</p>
      <p><b>Lesbarkeitsgrad:</b> ${r.lesbarkeitsgrad || "–"}</p>
      <p><b>Flesch-Wert:</b> ${r.flesch_reading_ease ? r.flesch_reading_ease.toFixed(2) : "-"}</p>
      <p><b>Satzanzahl:</b> ${r.sentence_count || "-"}</p>
      <p><b>Ø Satzlänge:</b> ${r.avg_sentence_length || "-"}</p>
      <p><b>Didaktische Relevanz:</b> Hilft, Texte für Zielgruppen passend zu gestalten. Für Unterrichtsmaterial sollte je nach Lernstand ein mittlerer bis hoher Wert angestrebt werden.</p>
    `;
    container.appendChild(readInfo);

    // ===============================
    // Aufgabenanalyse
    // ===============================
    const tasksContainer = el("div", "tasks");
    container.appendChild(tasksContainer);

    let index = 0;

    function renderTask(task) {
      const block = el("div", "border rounded p-4 mb-4 shadow-sm");
      block.innerHTML = `
        <h4>🧩 Aufgabe ${task.task_id}</h4>
        <p><b>Ähnlichkeit:</b> ${(task.similarity * 100).toFixed(1)}%</p>
        <p><b>Studentenlösung (SL):</b><br><pre>${task.student_answer}</pre></p>
        <p><b>Analyse (Unterschiede zu ML):</b><br><pre>${task.feedback}</pre></p>
      `;
      const btn = el("button", "btn btn-primary mt-2", "➡️ Nächste Aufgabe analysieren");
      btn.addEventListener("click", () => showNextTask());
      block.appendChild(btn);
      return block;
    }

    function showNextTask() {
      if (index < s.tasks.length) {
        tasksContainer.appendChild(renderTask(s.tasks[index]));
        index++;
        if (index === s.tasks.length) {
          const end = el("p", "mt-4 text-green-700 font-bold", "✅ Alle Aufgaben wurden analysiert.");
          tasksContainer.appendChild(end);
        }
      }
    }

    // Ersten Task anzeigen
    showNextTask();

  } catch (err) {
    loading.textContent = "❌ Fehler: " + err.message;
  }
})();
