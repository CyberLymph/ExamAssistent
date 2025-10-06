document.addEventListener("DOMContentLoaded", () => {
  const btnGenerate = document.getElementById("btn-generate");
  const generateFile = document.getElementById("generate-file");
  const generateFeedback = document.getElementById("generateFeedback");
  const generatePreview = document.getElementById("generatePreview");
  const btnExport = document.getElementById("btn-export");
  const generatePdfLink = document.getElementById("generatePdfLink");

  const btnCompare = document.getElementById("btn-compare");
  const compareFiles = document.getElementById("compare-files");
  const compareFeedback = document.getElementById("compareFeedback");
  const compareResult = document.getElementById("compareResult");

  let currentExportPdf = null;

  // -------------------------------
  // Feedback beim PDF Upload (Lösung)
  // -------------------------------
  generateFile.addEventListener("change", () => {
    if (generateFile.files.length === 1) {
      generateFeedback.innerText = `✅ ${generateFile.files[0].name} hochgeladen`;
    } else {
      generateFeedback.innerText = "";
    }
  });

  // -------------------------------
  // Lösung generieren
  // -------------------------------
  btnGenerate.addEventListener("click", async () => {
    if (generateFile.files.length !== 1) {
      generatePreview.style.display = "block";
      generatePreview.innerText = "⚠️ Bitte genau 1 PDF-Datei auswählen.";
      return;
    }

    generatePreview.style.display = "block";
    generatePreview.innerText = "⏳ Generiere Vorschau...";
    generatePdfLink.innerText = "";
    btnExport.style.display = "none";
    currentExportPdf = null;

    const formData = new FormData();
    formData.append("pdf", generateFile.files[0]);

    try {
      const res = await fetch("/api/generate-solution", {
        method: "POST",
        headers: { "X-CSRFToken": window.CSRF_TOKEN },
        body: formData,
      });

      const data = await res.json();
      if (data.solution) {
        generatePreview.innerText = data.solution;
        if (data.export_pdf) {
          currentExportPdf = data.export_pdf;
          btnExport.style.display = "inline-block";
        }
      } else {
        generatePreview.innerText = "⚠️ " + JSON.stringify(data);
      }
    } catch (err) {
      generatePreview.innerText = "❌ Fehler: " + err.message;
    }
  });

  // -------------------------------
  // Exportieren
  // -------------------------------
  btnExport.addEventListener("click", () => {
    if (!currentExportPdf) {
      generatePdfLink.innerText = "⚠️ Kein Export verfügbar.";
      return;
    }
    const fileName = currentExportPdf.split("/").pop();
    generatePdfLink.innerHTML = `<a href="/${currentExportPdf}" target="_blank" download="${fileName}">📄 PDF herunterladen</a>`;
    generatePreview.style.display = "none"; // Vorschau ausblenden
    btnExport.style.display = "none";
  });

  // -------------------------------
  // Feedback beim Upload (Vergleichen)
  // -------------------------------
  compareFiles.addEventListener("change", () => {
    if (compareFiles.files.length > 0) {
      compareFeedback.innerText = Array.from(compareFiles.files)
        .map((f, i) => `✅ Datei ${i + 1}: ${f.name}`)
        .join(" | ");
    } else {
      compareFeedback.innerText = "";
    }
  });

  // -------------------------------
  // Musterlösung vergleichen
  // -------------------------------
  btnCompare.addEventListener("click", async () => {
    if (compareFiles.files.length !== 2) {
      compareResult.innerText = "⚠️ Bitte genau 2 PDF-Dateien auswählen.";
      return;
    }

    compareResult.innerText = "⏳ Lade Dateien hoch und vergleiche...";

    const formData = new FormData();
    formData.append("file1", compareFiles.files[0]);
    formData.append("file2", compareFiles.files[1]);

    try {
      const res = await fetch("/api/compare-solutions", {
        method: "POST",
        headers: { "X-CSRFToken": window.CSRF_TOKEN },
        body: formData,
      });

      const data = await res.json();
      if (data.tasks) {
        compareResult.innerHTML = data.tasks
          .map((task, idx) => `<p><strong>Aufgabe ${idx + 1}:</strong> ${task.feedback}</p>`)
          .join("");
      } else if (data.similarity_score !== undefined) {
        compareResult.innerText = `✅ Ähnlichkeit: ${(data.similarity_score * 100).toFixed(2)} %`;
      } else {
        compareResult.innerText = "⚠️ " + JSON.stringify(data);
      }
    } catch (err) {
      compareResult.innerText = "❌ Fehler: " + err.message;
    }
  });
});
