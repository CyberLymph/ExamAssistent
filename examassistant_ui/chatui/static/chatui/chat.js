const elMessages = document.getElementById("messages");
const elForm = document.getElementById("form");
const elInput = document.getElementById("input");
const elSend = document.getElementById("send");
const elFile = document.getElementById("file");
const elUploadStatus = document.getElementById("uploadStatus");

function ensureChatId(){
  let id = localStorage.getItem("chat_id");
  if (!id) {
    const stamp = new Date().toISOString().slice(0,10);
    const rand = Math.random().toString(36).slice(2,8);
    id = `${stamp}-${rand}`;
    localStorage.setItem("chat_id", id);
  }
  return id;
}
const CHAT_ID = ensureChatId();

function addMsg(role, content){
  const div = document.createElement("div");
  div.className = `msg ${role === 'user' ? 'msg--user' : 'msg--bot'}`;
  div.textContent = content;
  elMessages.appendChild(div);
  elMessages.scrollTop = elMessages.scrollHeight;
}

elFile.addEventListener("change", () => {
  const f = elFile.files && elFile.files[0];
  if (!f) { elUploadStatus.textContent = ""; return; }
  if (f.type !== "application/pdf") {
    elUploadStatus.textContent = "Nur PDF erlaubt.";
    return;
  }
  const mb = (f.size/(1024*1024)).toFixed(2);
  elUploadStatus.textContent = `📎 ${f.name} (${mb} MB) bereit zum Senden`;
});

elForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = elInput.value.trim();
  const f = elFile.files && elFile.files[0];
  if (!text && !f) return;

  addMsg('user', text || (f ? `📎 ${f.name}` : ''));
  elInput.value = '';
  elSend.disabled = true;

  const body = { chat_id: CHAT_ID, content: text };
  if (f){
    const b64 = await fileToBase64(f);
    body.attachment = {
      file_name: f.name,
      content_base64: b64.split(',')[1],
      file_type: 'pdf'
    };
  }

  try{
    const res = await fetch("/api/message", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify(body)
    });
    let data = {};
    try { data = await res.json(); } catch {}
    if (!res.ok){
      addMsg('assistant', data.error || `Fehler: ${res.status}`);
      elUploadStatus.textContent = "⚠️ Senden fehlgeschlagen.";
      return;
    }
    addMsg('assistant', data.reply || '(keine Antwort)');
    if (f){
      elUploadStatus.textContent = data.saved_file
        ? `✔️ Gespeichert: ${data.saved_file}`
        : `✔️ PDF gesendet.`;
      elFile.value = "";
    }
  }catch(e){
    addMsg('assistant', `Netzwerkfehler: ${e}`);
    elUploadStatus.textContent = "❌ Netzwerkfehler.";
  }finally{
    elSend.disabled = false;
  }
});

function fileToBase64(file){
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

// ENTER zum Senden (Shift+Enter = Zeilenumbruch)
elInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    elForm.requestSubmit();
  }
});
