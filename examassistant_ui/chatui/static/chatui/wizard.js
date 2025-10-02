// Elemente
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
const btnExport = document.getElementById("btnExport");
const elExportStatus = document.getElementById("exportStatus");

// Chat-ID
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

// Wizard State
let topics = [];
let currentTopicIndex = 0;
let finishedTopics = false;

let current = { run_id: null, text: "", json: null, schema_type: "default", retried: false };

// Step Navigation
btnToStep2.addEventListener("click", () => {
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

  // Preview erst jetzt zeigen, initial leer
  previewCard.hidden = false;
  elPreviewPanel.innerHTML = '<p class="muted">Noch keine Aufgaben übernommen.</p>';
  btnExport.hidden = true; // erst nach "Fertig mit Themen"
});

function setTopicHeading(){
  const t = topics[currentTopicIndex];
  elTopicTitle.textContent = t ? `${t.name}` : `Thema ${currentTopicIndex+1}`;
  btnPrevTopic.disabled = currentTopicIndex === 0;
  btnNextTopic.disabled = currentTopicIndex >= topics.length - 1;
  // "Fertig mit Themen" nur beim letzten Thema anzeigen
  btnFinishTopics.hidden = (currentTopicIndex !== topics.length - 1);
}

// Generate/Accept/Decline
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
    const r = await fetch("/api/task/generate", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({
        chat_id: CHAT_ID,
        prompt,
        schema_type,
        retry_of
      })
    });
    const data = await r.json();
    if (!r.ok){
      elGenText.textContent = data.error || "Fehler bei der Generierung.";
      elGenMeta.hidden = true;
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
  if (!current.run_id) return;
  try{
    const r = await fetch("/api/task/accept", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({
        chat_id: CHAT_ID,
        run_id: current.run_id,
        text: current.text,
        json: current.json,
        schema_type: current.schema_type
      })
    });
    const data = await r.json();
    if (!r.ok){
      elGenText.textContent = data.error || "Konnte nicht übernehmen.";
      return;
    }
    // UI aufräumen
    elGenPrompt.value = "";
    elGenText.textContent = "";
    elGenMeta.hidden = true;

    // Preview aktualisieren
    await refreshPreview();

    // Automatisch zum nächsten Thema, falls vorhanden
    if (currentTopicIndex < topics.length - 1){
      currentTopicIndex++;
      setTopicHeading();
    } else {
      // sind schon im letzten Thema – Next deaktivieren
      btnNextTopic.disabled = true;
      btnFinishTopics.hidden = false; // bleibt sichtbar
    }
  }catch(e){
    elGenText.textContent = `Netzwerkfehler: ${e}`;
  }
});

btnDecline.addEventListener("click", async () => {
  await generate(current.run_id || null); // Alternative
});

// Finish Topics
btnFinishTopics.addEventListener("click", async () => {
  finishedTopics = true;
  await refreshPreview(); // damit Button-Status korrekt gesetzt wird
  // Export-Button nur zeigen, wenn es mind. 1 Aufgabe gibt
  btnExport.hidden = btnExport.dataset.hasItems !== "1";
});

// Preview rendering
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
    const j = it.json || {};
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
      const j = it.json || {};
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
          // default schema: task ist string (dein Schema); fallback auf it.text
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
  try{
    const r = await fetch("/api/task/accepted_list", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ chat_id: CHAT_ID })
    });
    const data = await r.json();
    if (!r.ok){
      elPreviewPanel.innerHTML = `<p class="muted">Fehler: ${escapeHtml(data.error||"")}</p>`;
      btnExport.dataset.hasItems = "0";
      return;
    }
    renderPreviewHTML(data.items || []);
    // Export-Button nur zeigen, wenn Themen fertig markiert UND Items vorhanden
    const hasItems = (btnExport.dataset.hasItems === "1");
    btnExport.hidden = !(finishedTopics && hasItems);
  }catch(e){
    elPreviewPanel.innerHTML = `<p class="muted">Netzwerkfehler: ${escapeHtml(e)}</p>`;
    btnExport.dataset.hasItems = "0";
    btnExport.hidden = true;
  }
}

// Export
btnExport.addEventListener("click", async () => {
  elExportStatus.textContent = "Exportiere PDF…";
  try{
    const subject = (elSubject?.value || "").trim();
    const title = subject || "Klausur";  // <-- Titel aus Fach
    const r = await fetch("/api/task/export", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({
        chat_id: CHAT_ID,
        title,
        subject: subject || null,
        topics
      })
    });
    const data = await r.json();
    if (!r.ok){
      elExportStatus.textContent = data.error || "Fehler beim Export.";
      return;
    }
    elExportStatus.innerHTML = `✅ Export fertig: <code>${data.pdf_path}</code>`;
  }catch(e){
    elExportStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});
