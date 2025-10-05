// generator.js

const elPrompt = document.getElementById("prompt");
const elResult = document.getElementById("result");
const elActions = document.getElementById("actions");
const elReadability = document.getElementById("readability");
const elStatus = document.getElementById("status");
const btnGenerate = document.getElementById("btnGenerate");
const btnAccept = document.getElementById("btnAccept");
const btnDecline = document.getElementById("btnDecline");
const btnExport = document.getElementById("btnExport");

// optional: Auswahl des Schemas (falls im Template vorhanden)
const elSchemaType = document.getElementById("schemaType");

// ---- IDs & Helpers ----
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

// Persistente EXAM_ID, damit /task/accept nie ohne exam_id aufgerufen wird
let EXAM_ID = localStorage.getItem("exam_id");
async function ensureExamInitialized(){
  if (!EXAM_ID){
    EXAM_ID = newExamId();
    localStorage.setItem("exam_id", EXAM_ID);
  }
  try{
    await fetch("/api/task/reset_exam", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ chat_id: CHAT_ID, exam_id: EXAM_ID })
    });
  }catch(_e){ /* UI kann ohne Reset weiterarbeiten */ }
}
// Beim Laden einmal initialisieren
ensureExamInitialized();

// ---- State ----
let current = { run_id: null, text: "", retried: false, json: null, schema: "default" };

// ---- UI ----
function showResult(text, rb){
  elResult.innerHTML = "";
  const card = document.createElement("div");
  card.className = "msg msg--bot";
  card.style.whiteSpace = "pre-wrap";
  card.textContent = text;
  elResult.appendChild(card);

  if (elReadability){
    const label = rb?.label || "";
    const flesch = rb?.flesch != null ? ` (Flesch: ${rb.flesch})` : "";
    elReadability.textContent = label ? `${label}${flesch}` : "";
  }
  if (elActions) elActions.style.display = "flex";
}

async function generate(retry_of=null){
  const prompt = elPrompt?.value?.trim?.() || "";
  if (!prompt){ elStatus.textContent = "Bitte Prompt eingeben."; return; }
  const schema_type = elSchemaType ? (elSchemaType.value || "default") : "default";

  elStatus.textContent = "Erzeuge Aufgabe…";
  btnGenerate.disabled = true;

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
      elStatus.textContent = (data && (data.error || data.detail)) || "Fehler";
      console.error("Generate failed:", r.status, data);
      return;
    }

    current.run_id = data.run_id;
    current.text   = data.text;
    current.json   = data.json || null;
    current.schema = data.schema || schema_type;

    showResult(data.text, data.readability);
    elStatus.textContent = "Fertig.";
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }finally{
    btnGenerate.disabled = false;
  }
}

btnGenerate?.addEventListener("click", () => {
  current.retried = false;
  generate(null);
});

btnAccept?.addEventListener("click", async () => {
  if (!current.run_id){ elStatus.textContent = "Bitte zuerst generieren."; return; }
  if (!EXAM_ID){ await ensureExamInitialized(); }

  // exam_id aus LocalStorage sicherstellen (falls anderer Tab sie geändert hat)
  EXAM_ID = (localStorage.getItem("exam_id") || EXAM_ID || "").trim();
  if (!EXAM_ID){
    elStatus.textContent = "Keine exam_id gesetzt.";
    return;
  }

  const payload = {
    chat_id: CHAT_ID,
    exam_id: EXAM_ID,            // <<< WICHTIG
    run_id: current.run_id,
    text: current.text,
    payload: current.json,       // <<< nur NOCH 'payload' senden
    schema_type: current.schema
  };
  console.debug("[ACCEPT payload]", payload);

  elStatus.textContent = "Übernehme in Entwurf…";
  try{
    const r = await fetch("/api/task/accept", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify(payload)
    });
    let data = {};
    try { data = await r.json(); } catch {}
    if (!r.ok){
      const msg = (data && (data.detail || data.error)) || `Fehler (${r.status})`;
      elStatus.textContent = msg;
      console.error("Accept failed:", r.status, data);
      return;
    }
    // Response „verschwindet“
    elResult.innerHTML = "";
    if (elActions) elActions.style.display = "none";
    if (elReadability) elReadability.textContent = "";
    elStatus.textContent = `Hinzugefügt. Aktuell insgesamt: ${data.count}.`;
    if (elPrompt) elPrompt.value = ""; // bereit für nächste Aufgabe
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});

btnDecline?.addEventListener("click", async () => {
  if (current.retried){
    // zweite Ablehnung → keine weitere Alternative, zurück zum Prompt
    elResult.innerHTML = "";
    if (elActions) elActions.style.display = "none";
    if (elReadability) elReadability.textContent = "";
    elStatus.textContent = "Nicht übernommen. Bitte neuen Prompt eingeben.";
    return;
  }
  current.retried = true;
  elStatus.textContent = "Erzeuge Alternative…";
  await generate(current.run_id);
});

// Optionaler Export-Button auf der Generator-Seite
btnExport?.addEventListener("click", async () => {
  if (!EXAM_ID){ await ensureExamInitialized(); }
  elStatus.textContent = "Exportiere PDF…";
  try{
    const subjectInput = document.getElementById("subject");
    const subject = subjectInput ? (subjectInput.value || "").trim() : "";
    const title = subject ? `Klausur: ${subject}` : "Klausur";

    const r = await fetch("/api/task/export_pdf", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({
        chat_id: CHAT_ID,
        exam_id: EXAM_ID,           // <<< WICHTIG
        title,
        subject: subject || null,
        topics: []                  // generator-Seite hat hier keine Liste; Wizard sendet sie
      })
    });
    const data = await r.json();
    if (!r.ok){
      elStatus.textContent = (data && (data.error || data.detail)) || "Fehler";
      console.error("Export failed:", r.status, data);
      return;
    }
    elStatus.innerHTML = `✅ Export fertig: <code>${data.pdf_path}</code>`;
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});
