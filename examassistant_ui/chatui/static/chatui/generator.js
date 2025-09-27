const elPrompt = document.getElementById("prompt");
const elResult = document.getElementById("result");
const elActions = document.getElementById("actions");
const elReadability = document.getElementById("readability");
const elStatus = document.getElementById("status");
const btnGenerate = document.getElementById("btnGenerate");
const btnAccept = document.getElementById("btnAccept");
const btnDecline = document.getElementById("btnDecline");
const btnExport = document.getElementById("btnExport");

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

let current = { run_id: null, text: "", retried: false };

function showResult(text, rb){
  elResult.innerHTML = "";
  const card = document.createElement("div");
  card.className = "msg msg--bot";
  card.style.whiteSpace = "pre-wrap";
  card.textContent = text;
  elResult.appendChild(card);

  elReadability.textContent = rb?.label ? `${rb.label}${rb.flesch?` (Flesch: ${rb.flesch})`:''}` : "";
  elActions.style.display = "flex";
}

async function generate(retry_of=null){
  const prompt = elPrompt.value.trim();
  if (!prompt){ elStatus.textContent = "Bitte Prompt eingeben."; return; }
  elStatus.textContent = "Erzeuge Aufgabe…";
  btnGenerate.disabled = true;

  try{
    const r = await fetch("/api/task/generate", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ chat_id: CHAT_ID, prompt, retry_of })
    });
    const data = await r.json();
    if (!r.ok){ elStatus.textContent = data.error || "Fehler"; return; }

    current.run_id = data.run_id;
    current.text = data.text;
    showResult(data.text, data.readability);
    elStatus.textContent = "Fertig.";
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }finally{
    btnGenerate.disabled = false;
  }
}

btnGenerate.addEventListener("click", () => {
  current.retried = false;
  generate(null);
});

btnAccept.addEventListener("click", async () => {
  if (!current.run_id){ return; }
  elStatus.textContent = "Übernehme in PDF-Entwurf…";
  try{
    const r = await fetch("/api/task/accept", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ chat_id: CHAT_ID, run_id: current.run_id, text: current.text })
    });
    const data = await r.json();
    if (!r.ok){ elStatus.textContent = data.error || "Fehler"; return; }
    // Response „verschwindet“
    elResult.innerHTML = "";
    elActions.style.display = "none";
    elReadability.textContent = "";
    elStatus.textContent = `Hinzugefügt. Aktuell insgesamt: ${data.count}.`;
    elPrompt.value = ""; // bereit für nächste Aufgabe
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});

btnDecline.addEventListener("click", async () => {
  if (current.retried){
    // zweite Ablehnung → keine weitere Alternative, zurück zum Prompt
    elResult.innerHTML = "";
    elActions.style.display = "none";
    elReadability.textContent = "";
    elStatus.textContent = "Nicht übernommen. Bitte neuen Prompt eingeben.";
    return;
  }
  current.retried = true;
  elStatus.textContent = "Erzeuge Alternative…";
  await generate(current.run_id);
});

btnExport.addEventListener("click", async () => {
  elStatus.textContent = "Exportiere PDF…";
  try{
    const r = await fetch("/api/task/export", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ chat_id: CHAT_ID, title: "Klausur-Entwurf" })
    });
    const data = await r.json();
    if (!r.ok){ elStatus.textContent = data.error || "Fehler"; return; }
    elStatus.innerHTML = `✅ Export fertig: <code>${data.pdf_path}</code>`;
  }catch(e){
    elStatus.textContent = `Netzwerkfehler: ${e}`;
  }
});
