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
  const f = elFile.files && elFile.files[0];
  if (!text && !f) return; // nichts zu senden

  addMsg('user', text || (f ? `📎 ${f.name}` : ''));
  elInput.value = '';
  elSend.disabled = true;

  // Body bauen
  const body = { content: text };
  if (f) {
    const b64 = await fileToBase64(f);
    body.attachment = {
      file_name: f.name,
      content_base64: b64.split(',')[1],
      file_type: 'pdf'
    };
  }

  try {
    const res = await fetch("/api/message", {
      method: "POST",
      headers: {"Content-Type":"application/json","X-CSRFToken": window.CSRF_TOKEN},
      body: JSON.stringify(body)
    });
    const data = await res.json();
    addMsg('assistant', data.reply || data.error || '(keine Antwort)');
  } catch (e){
    addMsg('assistant', `Fehler: ${e}`);
  } finally {
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

// ENTER zum Senden  (Shift + Enter für zeilenumbruch)
elInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();     
    elForm.requestSubmit(); 
  }
});

