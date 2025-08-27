const elMessages = document.getElementById("messages");
const elForm = document.getElementById("form");
const elInput = document.getElementById("input");
const elSend = document.getElementById("send");
const elFile = document.getElementById("file");
const elUploadStatus = document.getElementById("uploadStatus");

function addMsg(role, content){
  const div = document.createElement("div");
  div.className = `msg ${role === 'user' ? 'msg--user' : 'msg--bot'}`;
  div.textContent = content;
  elMessages.appendChild(div);
  elMessages.scrollTop = elMessages.scrollHeight;
}

elForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = elInput.value.trim();
  if (!text) return;
  addMsg('user', text);
  elInput.value = '';
  elSend.disabled = true;
  try {
    const res = await fetch("/api/message", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify({ content: text })
    });
    const data = await res.json();
    addMsg('assistant', data.reply || data.error || '(keine Antwort)');
  } catch (e){
    addMsg('assistant', `Fehler: ${e}`);
  } finally {
    elSend.disabled = false;
  }
});

elFile.addEventListener("change", async (e) => {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  if (f.type !== 'application/pdf'){
    elUploadStatus.textContent = 'Nur PDF-Dateien sind erlaubt.';
    return;
  }
  const b64 = await fileToBase64(f);
  try {
    const res = await fetch('/api/attachment', {
      method: 'POST',
      headers: {'Content-Type':'application/json','X-CSRFToken': window.CSRF_TOKEN},
      body: JSON.stringify({ file_name: f.name, content_base64: b64.split(',')[1], file_type: 'pdf' })
    });
    const data = await res.json();
    elUploadStatus.textContent = data.ok ? `✔️ ${f.name} hochgeladen.` : `⚠️ Upload-Fehler.`;
  } catch (e){
    elUploadStatus.textContent = `❌ Upload fehlgeschlagen: ${e}`;
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
