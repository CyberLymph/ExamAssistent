(function () {
  // ======= DOM ELEMENTE =======
  const genFile=document.getElementById("genFile"),
        btnGenPreview=document.getElementById("btnGenPreview"),
        genFeedback=document.getElementById("genFeedback"),
        genInfo=document.getElementById("genInfo"),
        genPreview=document.getElementById("genPreview"),
        toStep2=document.getElementById("toStep2"),
        progressBar=document.getElementById("progressBar"),
        step1=document.getElementById("step1"),
        step2=document.getElementById("step2"),
        step3=document.getElementById("step3"),
        backTo1=document.getElementById("backTo1"),
        cmpFile1=document.getElementById("cmpFile1"),
        cmpFile2=document.getElementById("cmpFile2"),
        cmpFb1=document.getElementById("cmpFb1"),
        cmpFb2=document.getElementById("cmpFb2"),
        cmpResult=document.getElementById("compareResult"),
        btnQuickCompare=document.getElementById("btnQuickCompare"),
        btnToStep3=document.getElementById("toStep3");

  let state={hasGenerated:false,quickDone:false,running:false};

  const show=(el)=>el?.classList.remove("hidden");
  const hide=(el)=>el?.classList.add("hidden");
  const setProgress=(p)=>progressBar.style.width=p;

  // ======= STEP 1 =======
  genFile?.addEventListener("change",()=>{
    if(genFile.files.length){
      genFeedback.textContent=`✅ ${genFile.files[0].name}`;
      genInfo.textContent="Bereit zur Analyse.";
    } else { genFeedback.textContent=""; genInfo.textContent=""; }
  });

  btnGenPreview?.addEventListener("click",async()=>{
    if(!genFile.files.length){genInfo.textContent="⚠️ Bitte PDF auswählen.";return;}
    genInfo.textContent="⏳ Generiere Lösung...";
    const fd=new FormData();fd.append("pdf",genFile.files[0]);
    try{
      const res=await fetch("http://127.0.0.1:8000/generate-solution",{method:"POST",body:fd});
      const data=await res.json();
      if(!res.ok) throw new Error(data.detail||"Fehler beim Generieren.");
      genPreview.textContent=data.solution||"(Keine Vorschau)";
      show(genPreview);
      genInfo.textContent="✅ Lösung generiert.";
      state.hasGenerated=true;
      toStep2.removeAttribute("disabled");
      setProgress("50%");
    }catch(e){genInfo.textContent="❌ Fehler: "+e.message;}
  });

  toStep2?.addEventListener("click",()=>{hide(step1);show(step2);setProgress("50%");});
  backTo1?.addEventListener("click",()=>{hide(step2);show(step1);setProgress("50%");});

  // ======= STEP 2 =======
  cmpFile1?.addEventListener("change",()=>cmpFb1.textContent=cmpFile1.files.length?`✅ ${cmpFile1.files[0].name}`:"");
  cmpFile2?.addEventListener("change",()=>cmpFb2.textContent=cmpFile2.files.length?`✅ ${cmpFile2.files[0].name}`:"");

  // ---- Darkmode-kompatible Anzeige des Vergleichsergebnisses ----
 const showCmpResult = (content) => {
  if (!content.includes("<")) content = `<pre>${content}</pre>`;

  content = content
    .replace(/background[^:>]*:\s*[^;>]+;?/gi, "")
    .replace(/color\s*:\s*(black|#000|rgb\s*\(0,\s*0,\s*0\)|#[0-2][0-9a-f]{2});?/gi, "")
    .replace(/!important/gi, "")
    .replace(/<span[^>]*>/gi, (m) => m.replace(/style="[^"]*"/gi, ""))
    .replace(/<div[^>]*style="[^"]*background[^"]*"[^>]*>/gi, "<div>")
    .replace(/<p[^>]*style="[^"]*background[^"]*"[^>]*>/gi, "<p>");

  cmpResult.innerHTML = content;
  cmpResult.classList.remove("hidden");

  Object.assign(cmpResult.style, {
    backgroundColor: "#141926",
    color: "#f8fafc",
    border: "1px solid var(--border)",
    padding: "14px 16px",
    borderRadius: "8px",
    whiteSpace: "pre-wrap"
  });

  cmpResult.querySelectorAll("*").forEach((el) => {
    el.style.backgroundColor = "transparent";
    el.style.color = "#f8fafc";
  });

  cmpResult.querySelectorAll("pre").forEach((pre) => {
    pre.style.backgroundColor = "transparent";
    pre.style.color = "#f8fafc";
    pre.style.border = "none";
  });
};

  async function runQuickCompare(){
    if(state.running)return;
    if(!cmpFile1.files.length||!cmpFile2.files.length){showCmpResult("⚠️ Bitte 2 PDFs auswählen.");return;}
    state.running=true;btnQuickCompare.disabled=true;
    showCmpResult("⏳ Quick-Vergleich läuft...");
    const fd=new FormData();
    fd.append("file1",cmpFile1.files[0]);
    fd.append("file2",cmpFile2.files[0]);
    fd.append("mode","quick");
    try{
      const res=await fetch("http://127.0.0.1:8000/compare-solutions",{method:"POST",body:fd});
      const data=await res.json();
      if(!res.ok) throw new Error(data.detail||"Fehler beim Vergleich.");
      if(data.mode==="quick"){
        const html = `
          <b>⚡ Quick-Vergleich</b><br>
          Ähnlichkeit: ${(data.quick_similarity*100).toFixed(2)} %<br>
          Lesbarkeitsgrad: ${data.readability?.lesbarkeitsgrad||"-"}
        `;
        showCmpResult(html);
        state.quickDone=true;setProgress("75%");show(btnToStep3);
        step2.classList.add("quickdone");
      }
    }catch(e){showCmpResult("❌ Fehler: "+e.message);}
    finally{state.running=false;btnQuickCompare.disabled=false;}
  }
  btnQuickCompare?.addEventListener("click",runQuickCompare);

  // ======= STEP 3 =======
  const loadingDetail=document.getElementById("loadingDetail"),
        metaDetail=document.getElementById("metaDetail"),
        simScoreEl=document.getElementById("simScore"),
        readLevelEl=document.getElementById("readLevel"),
        gridDetail=document.getElementById("gridDetail"),
        colML=document.getElementById("colML"),
        colSL=document.getElementById("colSL"),
        endMsg=document.getElementById("endMsg");

  const fmtPercent=(v)=>typeof v==="number"?(v*100).toFixed(1)+" %":"–";
  const cleanText=(t)=>t?.replace(/Klausur:.*|Name:.*|Vorname:.*|Matrikelnummer:.*|Thema:.*|Gewichtung:.*|Erstellt am:.*|Themen & Gewichtungen.*|%/gi,"").trim();

function renderAll(tasks, summary) {
  colML.innerHTML = "";
  colSL.innerHTML = "";

  tasks.forEach((t, idx) => {
    const divider = `<hr style="border:1px solid #eee; margin:12px 0;">`;

    // ===== Hilfsfunktionen =====
    const getAnswer = (...keys) =>
      keys.map((k) => t[k]).find((v) => v && v.trim && v.trim() !== "");

    const getText = (...keys) =>
      keys.map((k) => t[k]).find((v) => typeof v === "string" && v.trim() !== "");

    const correct = getAnswer("correct_answer", "solution", "answer_correct", "model_solution");
    const studentAns = getAnswer("student_answer", "student_choice", "answer_given", "student_result", "response");
    const questionText = getText("question", "task_text", "prompt", "aufgabe");

    // === Musterlösung ===
    let modelContent = "";
    if (t.task_type === "multiple_choice" && Array.isArray(t.options)) {
      modelContent = `
        ${questionText || ""}
        <ul style="margin-top:6px; padding-left:20px;">
          ${t.options.map((opt, i) => `
            <li ${opt === correct ? 'style="color:#22c55e;font-weight:600;"' : ""}>
              ${String.fromCharCode(65 + i)}) ${opt}
            </li>`).join("")}
        </ul>
        <p style="margin-top:6px;"><b>✅ Richtige Antwort:</b> ${correct || "-"}</p>
      `;
    } else if (t.task_type === "calculation") {
      modelContent = `
        ${questionText || ""}
        <p style="margin-top:6px;"><b>🔢 Lösung:</b> ${correct || "(Keine Musterlösung)"}</p>
      `;
    } else {
      modelContent = `
        <div class="solution-text">
          ${
            t.model_solution
              ?.replace(/^\s+/gm, "")
              ?.replace(/(\s*)(Antwort\s*\d*?:)/g, "<br><br>$2")
              ?.replace(/(Antwort\s*\d*?:)(\s*)(?=[A-ZÄÖÜa-zäöü])/g, "$1<br>")
              || "(Keine Musterlösung)"
          }
        </div>
      `;
    }

    const ml = document.createElement("div");
    ml.className = "card";
    ml.innerHTML = `
      <b>${t.task_id || "Aufgabe"}</b>
      ${modelContent}
      ${idx < tasks.length - 1 ? divider : ""}
    `;
    colML.appendChild(ml);

    // === Studentenlösung ===
    let studentContent = "";
    if (t.task_type === "multiple_choice" && Array.isArray(t.options)) {
      studentContent = `
        ${questionText || ""}
        <ul style="margin-top:6px; padding-left:20px;">
          ${t.options.map((opt, i) => `
            <li ${opt === studentAns ? 'style="color:#facc15;font-weight:600;"' : ""}>
              ${String.fromCharCode(65 + i)}) ${opt}
            </li>`).join("")}
        </ul>
        <p style="margin-top:6px;">
          <b>🧩 Gewählte Antwort:</b> ${studentAns || "-"}<br>
          ${
            correct && studentAns
              ? studentAns === correct
                ? '<span style="color:#22c55e;">✅ korrekt</span>'
                : '<span style="color:#ef4444;">❌ falsch</span>'
              : ""
          }
        </p>
      `;
    } else if (t.task_type === "calculation") {
      studentContent = `
        ${questionText || ""}
        <p style="margin-top:6px;">
          <b>🧮 Berechnete Antwort:</b> ${studentAns || "(Keine Antwort)"}<br>
          ${
            correct && studentAns
              ? studentAns.trim() === correct.trim()
                ? '<span style="color:#22c55e;">✅ korrekt</span>'
                : '<span style="color:#ef4444;">❌ falsch</span>'
              : ""
          }
        </p>
      `;
    } else {
      studentContent = `
        <div class="solution-text">
          ${
            cleanText(studentAns)
              ?.replace(/^\s+/gm, "")
              ?.replace(/(\s*)(Antwort\s*\d*?:)/g, "<br><br>$2")
              ?.replace(/(Antwort\s*\d*?:)(\s*)(?=[A-ZÄÖÜa-zäöü])/g, "$1<br>")
              || "(Keine SL)"
          }
        </div>
      `;
    }

    const sl = document.createElement("div");
    sl.className = "card";
    sl.innerHTML = `
      <b>${t.task_id || "Aufgabe"}</b>
      ${studentContent}
      <div class="feedback-box">
        <b>Ähnlichkeit:</b> ${fmtPercent(t.similarity)}<br>
        <b>Lesbarkeitsgrad (SL):</b> ${t.readability || "-"}<br>
        <b>Satzanzahl:</b> ${t.satzanzahl || "-"}<br>
        <b>Ø Satzlänge:</b> ${t.satzlänge || "-"}<br><br>
        <b>Feedback:</b><br>${
          t.feedback?.replaceAll("\n", "<br>") || "(Kein Feedback)"
        }
      </div>
      ${idx < tasks.length - 1 ? divider : ""}
    `;
    colSL.appendChild(sl);
  });







  // === Hover-Popup Setup (verbesserte Version mit Scrollfix) ===
// === Hover-Popup Setup (fixiert, scroll- und hoverbar) ===
const popup = document.createElement("div");
popup.className = "feedback-popup";
document.body.appendChild(popup);

let activeCard = null;

const showPopup = (evt, html) => {
  popup.innerHTML = html;
  popup.style.display = "block";
  popup.style.position = "fixed"; // bleibt am Bildschirm, nicht an der Maus
  const rect = evt.currentTarget.getBoundingClientRect();

  // Positionierung rechts neben der Karte, aber innerhalb des Viewports
  const left = Math.min(window.innerWidth - 450, rect.right + 20);
  const top = Math.max(60, Math.min(rect.top, window.innerHeight - popup.offsetHeight - 20));

  popup.style.left = `${left}px`;
  popup.style.top = `${top}px`;
  activeCard = evt.currentTarget;
};

const hidePopup = (e) => {
  // Popup nur schließen, wenn Maus NICHT über Karte ODER Popup ist
  if (
    !popup.contains(e.relatedTarget) &&
    !activeCard?.contains(e.relatedTarget)
  ) {
    popup.style.display = "none";
    activeCard = null;
  }
};

// Event-Delegation für alle Studentenkarten
colSL.querySelectorAll(".card").forEach((card) => {
  const fb = card.querySelector(".feedback-box");
  if (!fb) return;
  const html = fb.innerHTML;
  fb.style.display = "none";

  card.addEventListener("mouseenter", (e) => showPopup(e, html));
  card.addEventListener("mouseleave", hidePopup);
});

// Popup verschwindet, wenn man selbst das Popup verlässt
popup.addEventListener("mouseleave", (e) => {
  if (!activeCard?.contains(e.relatedTarget)) {
    popup.style.display = "none";
    activeCard = null;
  }
});


}


  async function loadDetailed(chat_id,run_id){
    hide(step2);show(step3);setProgress("90%");
    try{
      const res=await fetch(`http://127.0.0.1:8000/detailed-analysis?chat_id=${chat_id}&run_id=${run_id}`);
      const data=await res.json();
      if(!res.ok) throw new Error(data.detail||"Analyse konnte nicht geladen werden.");
      const s=data.summary;
      const tasks=Array.isArray(s.tasks)?s.tasks:[];
      if(!tasks.length) throw new Error("Keine Aufgaben gefunden.");

      simScoreEl.textContent=fmtPercent(s.similarity_score);
      readLevelEl.textContent=s.readability_metrics?.lesbarkeitsgrad||"–";

      hide(loadingDetail);show(metaDetail);show(gridDetail);
      renderAll(tasks, s);
      setProgress("100%");
    } catch (e) {
      loadingDetail.textContent="❌ Fehler: "+e.message;
    }
  }

  btnToStep3?.addEventListener("click", async () => {
    if (!state.quickDone || state.running) return;
    state.running = true;
    btnToStep3.textContent = "⏳ Detaillierte Analyse läuft...";

    const fd = new FormData();
    fd.append("file1", cmpFile1.files[0]);
    fd.append("file2", cmpFile2.files[0]);
    fd.append("mode", "detailed");
    fd.append("chat_id", "default");

    try {
      const res = await fetch("http://127.0.0.1:8000/compare-solutions", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Fehler bei Analyse.");

      if (data.mode === "detailed" && data.run_id) {
        await loadDetailed(data.chat_id, data.run_id);
      } else {
        showCmpResult("⚠️ Keine Analyse-Daten.");
      }
    } catch (e) {
      showCmpResult("❌ Fehler: " + e.message);
    } finally {
      btnToStep3.textContent = "Weiter ➜ Detaillierte Analyse";
      state.running = false;
    }
  });
})();
