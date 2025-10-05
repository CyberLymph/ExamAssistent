// wizard.js

// ---------- CSRF Helpers ----------
const _cookieGetter =
  window.getCookie ||
  function getCookie(name) {
    const m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  };

function getCsrfToken() {
  return window.CSRF_TOKEN || _cookieGetter('csrftoken');
}

// einmalig: falls beim ersten Aufruf kein Cookie vorhanden war, Seite 1x neu laden
(function ensureCsrfOnce() {
  const token = getCsrfToken();
  const didReload = sessionStorage.getItem('csrf_reload_done') === '1';
  if (!token && !didReload) {
    console.warn('Kein CSRF-Token vorhanden – lade einmal neu, um ihn zu setzen …');
    sessionStorage.setItem('csrf_reload_done', '1');
    window.location.reload();
  }
})();

// zentraler Fetch-Wrapper mit CSRF + Cookies + 403-Recovery
async function fetchWithCsrf(url, opts = {}) {
  const token = getCsrfToken();
  const headers = new Headers(opts.headers || {});
  if (!headers.has('Content-Type') && opts.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('X-CSRFToken', token);

  const res = await fetch(url, {
    credentials: 'same-origin', // Cookies IMMER mitsenden (gleiche Origin)
    ...opts,
    headers,
  });

  if (res.status === 403) {
    // CSRF-Cookie fehlt/ist ungültig -> Cookie neu holen und neu laden
    console.warn('403 von Server – versuche CSRF-Cookie neu zu holen …');
    sessionStorage.removeItem('csrf_reload_done');
    try {
      await fetch(window.location.pathname, { credentials: 'same-origin' });
    } catch {}
    window.location.reload();
  }

  return res;
}

// ---------- DOM Elemente ----------
const elSubject = document.getElementById("subject");
const elTopicCount = document.getElementById("topicCount");
const elTopicsList = document.getElementById("topicsList");
const btnToStep2 = document.getElementById("toStep2");
const btnBuildTopics = document.getElementById("buildTopics");
const btnToStep3 = document.getElementById("toStep3");

const elTopicTitle = document.getElementById("topicTitle");
const elSchemaType = document.getElementById("schemaType");
const elGenPrompt = document.getElementById("genPrompt");
const btnGenerate = document.getElementById("btnGenerate");
const elGenText = document.getElementById("genText");
const elGenMeta = document.getElementById("genMeta");
const elReadability = document.getElementById("readabilityBadge");
const btnAccept = document.getElementById("btnAccept");
const btnDecline = document.getElementById("btnDecline");

const btnPrevTopic = document.getElementById("prevTopic");
const btnNextTopic = document.getElementById("nextTopic");
const btnFinishTopics = document.getElementById("btnFinishTopics");

const previewCard = document.getElementById("previewCard");
const elPreviewPanel = document.getElementById("previewPanel");
const btnExport = document.getElementById("btnExport");          // PDF
const btnExportDocx = document.getElementById("btnExportDocx");  // DOCX (NEU)
const elExportStatus = document.getElementById("exportStatus");

// ---------- Chat/Exam IDs ----------
function ensureChatId(){
  let id = localStorage.getItem("chat_id");
  if (!id){
    const stamp = new Date().toISOString().slice(0,10);
    const rand = Math.random().toString(36).slice(2,8);
    id = `${stamp}-${rand}`;
    localStorage.setItem("chat_id", id);
  }
  return id;
}
const CHAT_ID = ensureChatId();

function newExamId(){
  const ts = new Date().toISOString().replace(/[:.]/g,"-");
  const rand = Math.random().toString(36).slice(2,8);
  return `${ts}_${rand}`;
}

// Persistente EXAM_ID (damit akzeptieren nie ohne exam_id passiert)
let EXAM_ID = localStorage.getItem("exam_id");
if (!EXAM_ID) {
  EXAM_ID = newExamId();
  localStorage.setItem("exam_id", EXAM_ID);
  // neuen Lauf im Backend initialisieren
  fetchWithCsrf("/api/task/reset_exam", {
    method: "POST",
    body: JSON.stringify({ chat_id: CHAT_ID, exam_id: EXAM_ID })
  }).catch(()=>{});
}

// ---------- Wizard State ----------
let topics = [];
let currentTopicIndex = 0;
let finishedTopics = false;

let current = { run_id: null, text: "", json: null, schema_type: "default", retried: false };

// ---------- Schritt-Navigation ----------
btnToStep2.addEventListener("click", async () => {
  // explizit neue Klausur starten (neuer Lauf)
  EXAM_ID = newExamId();
  localStorage.setItem("exam_id", EXAM_ID);
  try{
    await fetchWithCsrf("/api/task/reset_exam", {
      method: "POST",
      body: JSON.stringify({ chat_id: CHAT_ID, exam_id: EXAM_ID })
    });
  }catch(_e){ /* Reset-Fehler ist nicht fatal für UI */ }

  document.getElementById("step1").hidden = true;
  document.getElementById("step2").hidden = false;
});

btnBuildTopics.addEventListener("click", () => {
  const n = Math.max(1, Math.min(20, parseInt(elTopicCount.value || "1", 10)));
  elTopicsList.innerHTML = "";
  for (let i=0;i<n;i++){
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <input class="input t-name" type="text" placeholder="Thema ${i+1}">
      <input class="input t-weight" type="number" placeholder="Punkte" min="0" step="1" style="max-width:120px">
    `;
    elTopicsList.appendChild(row);
  }
  btnToStep3.disabled = false;
});

btnToStep3.addEventListener("click", () => {
  // Themen einsammeln
  topics = Array.from(elTopicsList.querySelectorAll(".row")).map((row, idx) => {
    const name = row.querySelector(".t-name").value.trim() || `Thema ${idx+1}`;
    const weight = parseInt(row.querySelector(".t-weight").value || "0", 10) || 0;
    return { name, weight };
  });
  currentTopicIndex = 0;
  finishedTopics = false;
  setTopicHeading();

  document.getElementById("step2").hidden = true;
  document.getElementById("step3").hidden = false;

  // Preview erst jetzt zeigen, initial leer und export verstecken
  previewCard.hidden = false;
  elPreviewPanel.innerHTML = '<p class="muted">Noch keine Aufgaben übernommen.</p>';
  btnExport.hidden = true;
  if (btnExportDocx) btnExportDocx.hidden = true;  // NEU: Word-Button initial verbergen
  btnExport.dataset.hasItems = "0";
});

function setTopicHeading(){
  const t = topics[currentTopicIndex];
  elTopicTitle.textContent = t ? `${t.name}` : `Thema ${currentTopicIndex+1}`;
  btnPrevTopic.disabled = currentTopicIndex === 0;
  btnNextTopic.disabled = currentTopicIndex >= topics.length - 1;
  // "Fertig mit Themen" nur beim letzten Thema anzeigen
  btnFinishTopics.hidden = (currentTopicIndex !== topics.length - 1);
}

// ---------- Generieren/Annehmen/Ablehnen ----------
function showResult(text, rb){
  elGenText.textContent = text || "";
  elGenMeta.hidden = !text;
  elReadability.textContent = rb?.label ? `${rb.label}${rb.flesch?` (Flesch: ${rb.flesch})`:''}` : "–";
}

async function generate(retry_of=null){
  const prompt = elGenPrompt.value.trim();
  if (!prompt){ elGenText.textContent = "Bitte Prompt eingeben."; elGenMeta.hidden = true; return; }
  btnGenerate.disabled = true;
  const schema_type = (elSchemaType.value || "default");

  try{
    const r = await fetchWithCsrf("/api/task/generate", {
      method: "POST",
      body: JSON.stringify({
        chat_id: CHAT_ID,
        prompt,
        schema_type,
        retry_of
      })
    });
    const data = await r.json();
    if (!r.ok){
      elGenText.textContent = (data && (data.error || data.detail)) || "Fehler bei der Generierung.";
      elGenMeta.hidden = true;
      console.error("Generate failed:", r.status, data);
      return;
    }
    current.run_id = data.run_id;
    current.text   = data.text;
    current.json   = data.json || null;
    current.schema_type = data.schema || schema_type;
    current.retried = !!retry_of;
    showResult(data.text, data.readability);
  }catch(e){
    elGenText.textContent = `Netzwerkfehler: ${e}`;
    elGenMeta.hidden = true;
  }finally{
    btnGenerate.disabled = false;
  }
}

btnGenerate.addEventListener("click", () => generate(null));

btnAccept.addEventListener("click", async () => {
  if (!current.run_id){
    elGenText.textContent = "Bitte zuerst eine Aufgabe generieren.";
    return;
  }
  // exam_id aus LocalStorage sicherstellen
  EXAM_ID = (localStorage.getItem("exam_id") || EXAM_ID || "").trim();
  if (!EXAM_ID){
    alert("Bitte Schritt 1 ausfüllen, damit eine Klausur-ID gesetzt wird.");
    return;
  }

  // >>> aktuelles Wizard-Thema als Pflicht-Topic setzen <<<
  const forcedTopic = (topics[currentTopicIndex]?.name || "").trim() || `Thema ${currentTopicIndex+1}`;

  // Robust: vorhandenes JSON klonen und Topic überschreiben
  const mergedJson = (current.json && typeof current.json === "object") ? { ...current.json } : {};
  mergedJson.topic = forcedTopic;                 // <-- HIER passiert die Magie

  const body = {
    chat_id: CHAT_ID,
    exam_id: EXAM_ID,
    run_id: current.run_id,
    text: current.text,
    payload: mergedJson,                          // statt current.json
    schema_type: current.schema_type
  };
  console.debug("[WIZARD ACCEPT body]", body);

  try{
    const r = await fetchWithCsrf("/api/task/accept", {
      method: "POST",
      body: JSON.stringify(body)
    });
    let data = {};
    try { data = await r.json(); } catch {}
    if (!r.ok){
      elGenText.textContent = (data && (data.detail || data.error)) || `Konnte nicht übernehmen. (${r.status})`;
      console.error("Accept failed:", r.status, data);
      return;
    }

    // UI aufräumen
    elGenPrompt.value = "";
    elGenText.textContent = "";
    elGenMeta.hidden = true;

    // Preview aktualisieren (jetzt gruppiert nach deinem Namen)
    await refreshPreview();
  }catch(e){
    elGenText.textContent = `Netzwerkfehler: ${e}`;
  }
});

btnDecline.addEventListener("click", async () => {
  // Einmalige Alternative anfordern
  await generate(current.run_id || null);
});

// Themenwechsel manuell
btnPrevTopic.addEventListener("click", () => {
  if (currentTopicIndex > 0){
    currentTopicIndex--;
    setTopicHeading();
  }
});
btnNextTopic.addEventListener("click", () => {
  if (currentTopicIndex < topics.length - 1){
    currentTopicIndex++;
    setTopicHeading();
  }
});

// Themen sind fertig
btnFinishTopics.addEventListener("click", async () => {
  finishedTopics = true;
  await refreshPreview(); // setzt Export-Sichtbarkeit abhängig von Items
  const hasItems = (btnExport.dataset.hasItems === "1");
  btnExport.hidden = !(finishedTopics && hasItems);
  if (btnExportDocx) btnExportDocx.hidden = !(finishedTopics && hasItems); // NEU
});

// ---------- Preview rendering ----------
function escapeHtml(s){
  return String(s || "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}

function renderPreviewHTML(items){
  if (!items || !items.length){
    elPreviewPanel.innerHTML = '<p class="muted">Noch keine Aufgaben übernommen.</p>';
    btnExport.dataset.hasItems = "0";
    return;
  }
  btnExport.dataset.hasItems = "1";

  const groups = new Map(); // topic -> items[]
  for (const it of items){
    const j = it.payload || it.json || {}; // fallback, falls alte Daten
    let topic = (j && typeof j === 'object' ? (j.topic || "") : "").trim();
    if (!topic) topic = "Allgemein";
    if (!groups.has(topic)) groups.set(topic, []);
    groups.get(topic).push(it);
  }

  // sortiere topics nach Eingabe-Reihenfolge (falls vorhanden)
  const order = topics.map(t => t.name);
  const sortedTopics = Array.from(groups.keys()).sort((a, b) => {
    const ia = order.indexOf(a), ib = order.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  let html = "";
  for (const topic of sortedTopics){
    const weight = (topics.find(t => t.name === topic)?.weight || 0);
    const weightTxt = weight > 0 ? ` — ${weight} Punkte` : "";
    html += `<div class="preview-topic"><h4>${escapeHtml(topic)}${weightTxt}</h4>`;
    const arr = groups.get(topic);
    arr.forEach((it, idx) => {
      const j = it.payload || it.json || {};
      const st = (it.schema_type || "default");
      let title = "", body = "";

      if (j && typeof j === 'object'){
        if (st === "mc"){
          title = j.title || "Multiple-Choice-Aufgabe";
          body  = (j.question || "");
          if (Array.isArray(j.options) && j.options.length){
            body += "\n" + j.options.map((o,i)=>`${String.fromCharCode(65+i)}) ${(o||{}).text||""}`).join("\n");
          }
        } else if (st === "calc"){
          title = j.title || "Rechenaufgabe";
          body  = (j.problem || "");
        } else {
          title = j.title || "Aufgabe";
          body  = typeof j.task === "string" && j.task ? j.task : (it.text || "");
        }
      } else {
        title = `Aufgabe ${idx+1}`;
        body  = it.text || "";
      }

      html += `
        <div class="preview-task">
          <div class="preview-task-title">Aufgabe ${idx+1}: ${escapeHtml(title)}</div>
          <div class="preview-task-text">${escapeHtml(body)}</div>
        </div>
      `;
    });
    html += `</div>`;
  }
  elPreviewPanel.innerHTML = html;
}

async function refreshPreview(){
  if (!EXAM_ID){
    elPreviewPanel.innerHTML = '<p class="muted">Noch keine Aufgaben übernommen.</p>';
    btnExport.dataset.hasItems = "0";
    btnExport.hidden = true;
    if (btnExportDocx) btnExportDocx.hidden = true; // NEU
    return;
  }
  try{
    const r = await fetchWithCsrf("/api/task/accepted_list", {
      method: "POST",
      body: JSON.stringify({ chat_id: CHAT_ID, exam_id: EXAM_ID })
    });
    let data = {};
    try { data = await r.json(); } catch {}
    if (!r.ok){
      elPreviewPanel.innerHTML = `<p class="muted">Fehler: ${escapeHtml((data && (data.error || data.detail)) || "")}</p>`;
      btnExport.dataset.hasItems = "0";
      btnExport.hidden = true;
      if (btnExportDocx) btnExportDocx.hidden = true; // NEU
      console.error("accepted_list failed:", r.status, data);
      return;
    }
    renderPreviewHTML((data && data.items) || []);
    const hasItems = (btnExport.dataset.hasItems === "1");
    btnExport.hidden = !(finishedTopics && hasItems);
    if (btnExportDocx) btnExportDocx.hidden = !(finishedTopics && hasItems); // NEU
  }catch(e){
    elPreviewPanel.innerHTML = `<p class="muted">Netzwerkfehler: ${escapeHtml(e)}</p>`;
    btnExport.dataset.hasItems = "0";
    btnExport.hidden = true;
    if (btnExportDocx) btnExportDocx.hidden = true; // NEU
  }
}

// ---------- Export ----------
btnExport.addEventListener("click", async () => {
  elExportStatus.textContent = "Exportiere PDF…";
  try{
    const subject = (elSubject?.value || "").trim();
    const title = subject ? `Klausur: ${subject}` : "Klausur";
    const r = await fetchWithCsrf("/api/task/export_pdf", {
      method: "POST",
      body: JSON.stringify({
        chat_id: CHAT_ID,
        exam_id: EXAM_ID,
        title,
        subject: subject || null,
        topics
      })
    });
    const data = await r.json();
    if (!r.ok){
      elExportStatus.textContent = (data && (data.error || data.detail)) || "Fehler beim Export.";
      console.error("export_pdf failed:", r.status, data);
      return;
    }
    elExportStatus.innerHTML = `✅ Export fertig: <code>${data.pdf_path}</code>`;
  }catch(e){
    elExportStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});

// ---------- Export (DOCX) ----------
if (btnExportDocx) {
  btnExportDocx.addEventListener("click", async () => {
    elExportStatus.textContent = "Exportiere Word…";
    try{
      const subject = (elSubject?.value || "").trim();
      const title = subject ? `Klausur: ${subject}` : "Klausur";
      const r = await fetchWithCsrf("/api/task/export_docx", {
        method: "POST",
        body: JSON.stringify({
          chat_id: CHAT_ID,
          exam_id: EXAM_ID,
          title,
          subject: subject || null,
          topics
        })
      });
      const data = await r.json();
      if (!r.ok){
        elExportStatus.textContent = (data && (data.error || data.detail)) || "Fehler beim Word-Export.";
        console.error("export_docx failed:", r.status, data);
        return;
      }
      elExportStatus.innerHTML = `✅ Word fertig: <code>${data.docx_path}</code>`;
    }catch(e){
      elExportStatus.textContent = `Netzwerkfehler: ${e}`;
    }
  });
}
