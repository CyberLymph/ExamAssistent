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

  const showCmpResult=(html)=>{cmpResult.innerHTML=html;show(cmpResult);};

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
        showCmpResult(`<b>⚡ Quick-Vergleich</b><br>Ähnlichkeit: ${(data.quick_similarity*100).toFixed(2)} %<br>Lesbarkeitsgrad: ${data.readability?.lesbarkeitsgrad||"-"}`);
        state.quickDone=true;setProgress("75%");show(btnToStep3);
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

  function renderAll(tasks, summary){
    colML.innerHTML="";colSL.innerHTML="";
    tasks.forEach((t, idx)=>{
      const divider = `<hr style="border:1px solid #eee; margin:12px 0;">`;

      // Musterlösung
      const ml=document.createElement("div");
      ml.className="card";
      ml.innerHTML = `
        <b>${t.task_id || "Aufgabe"}</b>
        <pre>${t.model_solution || "(Keine ML)"}</pre>
        <div class="feedback-box">
          <b>Lesbarkeitsgrad (ML):</b> ${summary.readability_metrics_model?.lesbarkeitsgrad || "-"}<br>
          <b>Satzanzahl:</b> ${summary.readability_metrics_model?.satzanzahl || "-"}<br>
          <b>Ø Satzlänge:</b> ${summary.readability_metrics_model?.satzlaenge || "-"}
        </div>
        ${idx < tasks.length - 1 ? divider : ""}
      `;
      colML.appendChild(ml);

      // Studentenlösung
      const sl=document.createElement("div");
      sl.className="card";
      sl.innerHTML = `
        <b>${t.task_id || "Aufgabe"}</b>
        <pre style="border-bottom:1px solid #ddd; padding-bottom:6px;">${cleanText(t.student_answer) || "(Keine SL)"}</pre>
        <div class="feedback-box">
          <b>Ähnlichkeit:</b> ${fmtPercent(t.similarity)}<br>
          <b>Lesbarkeitsgrad (SL):</b> ${t.readability || "-"}<br>
          <b>Satzanzahl:</b> ${t.satzanzahl || "-"}<br>
          <b>Ø Satzlänge:</b> ${t.satzlänge || "-"}<br><br>
          <b>Feedback:</b><br>${t.feedback?.replaceAll("\n","<br>") || "(Kein Feedback)"}
        </div>
        ${idx < tasks.length - 1 ? divider : ""}
      `;
      colSL.appendChild(sl);
    });
    endMsg.classList.remove("hidden");
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
