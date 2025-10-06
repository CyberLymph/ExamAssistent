(function () {
  // ------------------------------
  // Elemente / DOM
  // ------------------------------
  const genFile = document.getElementById("genFile");
  const btnGenPreview = document.getElementById("btnGenPreview");
  const genFeedback = document.getElementById("genFeedback");
  const genInfo = document.getElementById("genInfo");
  const genPreview = document.getElementById("genPreview");
  const genDownloadLink = document.getElementById("genDownloadLink");
  const toStep2 = document.getElementById("toStep2");
  const progressBar = document.getElementById("progressBar");

  const step1 = document.getElementById("step1");
  const step2 = document.getElementById("step2");
  const backTo1 = document.getElementById("backTo1");
  const cmpFile1 = document.getElementById("cmpFile1");
  const cmpFile2 = document.getElementById("cmpFile2");
  const cmpFb1 = document.getElementById("cmpFb1");
  const cmpFb2 = document.getElementById("cmpFb2");
  const cmpResult = document.getElementById("compareResult");

  // ------------------------------
  // Zustand
  // ------------------------------
  let state = {
    hasGenerated: false,
  };

  // ------------------------------
  // Hilfsfunktionen
  // ------------------------------
  function show(el) {
    if (el) el.classList.remove("hidden");
  }
  function hide(el) {
    if (el) el.classList.add("hidden");
  }

  // ------------------------------
  // Datei auswählen
  // ------------------------------
  genFile?.addEventListener("change", () => {
    if (genFile.files.length) {
      genFeedback.textContent = `✅ ${genFile.files[0].name}`;
      genInfo.textContent = "Bereit zur Analyse.";
    } else {
      genFeedback.textContent = "";
      genInfo.textContent = "";
    }
  });

  // ------------------------------
  // Lösung generieren
  // ------------------------------
  btnGenPreview?.addEventListener("click", async () => {
    if (!genFile.files.length) {
      genInfo.textContent = "⚠️ Bitte eine PDF auswählen.";
      return;
    }

    genInfo.textContent = "⏳ Generiere Lösung...";
    const fd = new FormData();
    fd.append("pdf", genFile.files[0]);

    try {
      const res = await fetch("/api/generate-solution", {
        method: "POST",
        headers: { "X-CSRFToken": window.CSRF_TOKEN || "" },
        body: fd,
      });
      const data = await res.json();

      if (!res.ok || data.error || data.detail)
        throw new Error(data.error || data.detail || "Fehler beim Generieren.");

      genPreview.textContent = data.solution || "(Keine Vorschau)";
      show(genPreview);

      if (data.export_pdf) {
        genDownloadLink.href = "/" + data.export_pdf.replace(/^\/+/, "");
        show(genDownloadLink);
      }

      genInfo.textContent = "✅ Lösung erfolgreich generiert.";
      state.hasGenerated = true;

      // Weiter aktivieren
      toStep2.removeAttribute("disabled");
      toStep2.style.cursor = "pointer";
      toStep2.title = "Weiter zur Vergleichsanalyse";
      progressBar.style.width = "50%";
    } catch (err) {
      genInfo.textContent = "❌ Fehler: " + err.message;
    }
  });

  // ------------------------------
  // Navigation – Weiter zu Schritt 2
  // ------------------------------
  toStep2?.addEventListener("click", () => {
    if (!state.hasGenerated) {
      genInfo.textContent =
        "⚠️ Bitte zuerst eine Lösung generieren, bevor du fortfährst.";
      return;
    }
    step1.classList.add("hidden");
    step2.classList.remove("hidden");
    progressBar.style.width = "100%";
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // ------------------------------
  // Navigation – Zurück zu Schritt 1
  // ------------------------------
  backTo1?.addEventListener("click", () => {
    step2.classList.add("hidden");
    step1.classList.remove("hidden");
    progressBar.style.width = "50%";
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // ------------------------------
  // Vergleichsanalyse
  // ------------------------------
  function showCmpResult(html) {
    cmpResult.innerHTML = html;
    show(cmpResult);
  }

  cmpFile1?.addEventListener("change", () => {
    cmpFb1.textContent = cmpFile1.files.length
      ? `✅ ${cmpFile1.files[0].name}`
      : "";
  });

  cmpFile2?.addEventListener("change", () => {
    cmpFb2.textContent = cmpFile2.files.length
      ? `✅ ${cmpFile2.files[0].name}`
      : "";
  });

  async function runCompare(mode) {
    if (!cmpFile1.files.length || !cmpFile2.files.length) {
      showCmpResult("⚠️ Bitte 2 PDFs auswählen (Muster & Student).");
      return;
    }

    const isQuick = mode === "quick";
    showCmpResult(
      isQuick
        ? "⏳ Quick-Vergleich läuft..."
        : "⏳ Detaillierte Analyse läuft..."
    );

    const fd = new FormData();
    fd.append("file1", cmpFile1.files[0]);
    fd.append("file2", cmpFile2.files[0]);
    fd.append("mode", mode);

    try {
      const res = await fetch("/api/compare-solutions", {
        method: "POST",
        headers: { "X-CSRFToken": window.CSRF_TOKEN || "" },
        body: fd,
      });

      const data = await res.json();
      if (!res.ok || data.error)
        throw new Error(data.error || `HTTP ${res.status}`);

      let out = "";
      if (data.quick_similarity !== undefined) {
        out += `⚡ Quick-Vergleich: ${(data.quick_similarity * 100).toFixed(
          2
        )} %<br>`;
      }
      if (data.similarity_score !== undefined) {
        out += `🔗 Gesamt-Ähnlichkeit: ${(data.similarity_score * 100).toFixed(
          2
        )} %<br><br>`;
      }

      if (Array.isArray(data.tasks) && data.tasks.length) {
        data.tasks.forEach((t) => {
          out += `
          <div style="margin-bottom:16px; border-bottom:1px solid #ddd; padding-bottom:10px;">
            <b>${t.task_id}:</b><br>
            <b style="color:#444;">Studentenantwort:</b><br>
            ${t.student_answer?.replace(/\n/g, "<br>") || "(keine Antwort)"}<br><br>
            <b style="color:#444;">Analyse:</b><br>
            ${t.feedback?.replace(/\n/g, "<br>") || "(keine Analyse)"}<br>
            <i>Ähnlichkeit: ${t.similarity || 0}%</i>
          </div>`;
        });
      }

      if (data.readability) {
        out += `<hr><b>📖 Lesbarkeitsanalyse:</b><br>
        Lesbarkeitsgrad: ${data.readability.lesbarkeitsgrad || "-"}<br>
        Satzanzahl: ${data.readability.satzanzahl || "-"}<br>
        Ø Satzlänge: ${
          data.readability.durchschnittliche_Satzlänge || "-"
        }<br>`;
      }

      if (data.summary)
        out += `<hr><b>🧾 Zusammenfassung:</b><br>${data.summary}<br>`;

      showCmpResult(out || "⚠️ Keine Ergebnisse gefunden.");
    } catch (e) {
      showCmpResult("❌ Fehler: " + e.message);
    }
  }
document
  .getElementById("btnDetailedCompare")
  ?.addEventListener("click", async () => {
    const result = await runCompare("detailed");
    // Nach Abschluss → Redirect zur Detailansicht
    const run_id_match = /([0-9TZ_]+_[a-f0-9]{8})/.exec(result?.summary || "");
    if (run_id_match) {
      window.location.href = `/detailed?chat_id=default&run_id=${run_id_match[1]}`;
    }
  });

  // Buttons verbinden
  document
    .getElementById("btnQuickCompare")
    ?.addEventListener("click", () => runCompare("quick"));
})();
