SMOKE_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Teaser Smoke UI</title>
    <style>
      :root {
        --bg: #f3f4f6;
        --panel: #ffffff;
        --line: #d1d5db;
        --text: #111827;
        --muted: #6b7280;
        --primary: #1f4cff;
        --primary2: #0d9488;
        --danger: #b42318;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      .wrap {
        max-width: 1180px;
        margin: 0 auto;
        padding: 20px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 16px;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 24px;
      }
      .sub {
        margin: 0 0 14px;
        color: var(--muted);
        font-size: 14px;
      }
      .form-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
      }
      @media (min-width: 900px) {
        .form-grid {
          grid-template-columns: 2fr 1fr 1fr 1fr;
        }
      }
      label {
        display: block;
        font-size: 13px;
        color: #374151;
        margin-bottom: 6px;
      }
      textarea, select, input, button {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 14px;
      }
      textarea {
        min-height: 180px;
        resize: vertical;
      }
      .actions {
        margin-top: 12px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .actions button {
        border: none;
        cursor: pointer;
        width: auto;
      }
      #promptBtn {
        background: var(--primary);
        color: #fff;
      }
      #imageBtn {
        background: var(--primary2);
        color: #fff;
      }
      #sampleBtn {
        background: #e5e7eb;
        color: #111827;
      }
      #status {
        margin-top: 12px;
        border: 1px solid #c7d2fe;
        background: #eef2ff;
        color: #1e3a8a;
        border-radius: 10px;
        font-size: 13px;
        padding: 10px 12px;
      }
      #status.error {
        border-color: #fecdca;
        background: #fef3f2;
        color: var(--danger);
      }
      .results {
        margin-top: 16px;
        display: grid;
        gap: 10px;
      }
      .box {
        border: 1px solid var(--line);
        border-radius: 10px;
        background: #fff;
        overflow: hidden;
      }
      .box-head {
        font-size: 13px;
        color: #374151;
        border-bottom: 1px solid var(--line);
        padding: 8px 10px;
        background: #f9fafb;
      }
      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 360px;
        overflow: auto;
        padding: 10px;
        font-size: 12px;
        line-height: 1.45;
        background: #0b1220;
        color: #dbe3ff;
      }
      .cut-grid {
        display: grid;
        gap: 10px;
        grid-template-columns: 1fr;
      }
      @media (min-width: 1100px) {
        .cut-grid {
          grid-template-columns: 1fr 1fr;
        }
      }
      .img-grid {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .img-card {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        background: #fff;
      }
      .img-card img {
        width: 100%;
        display: block;
        aspect-ratio: 1 / 1;
        object-fit: cover;
        background: #f3f4f6;
      }
      .img-meta {
        font-size: 12px;
        color: var(--muted);
        padding: 6px 8px;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="panel">
        <h1>Teaser Smoke UI</h1>
        <p class="sub">Prompt preview and image generation test UI.</p>

        <div class="form-grid">
          <div>
            <label for="sourceText">Text source or synopsis</label>
            <textarea id="sourceText" placeholder="Paste text..."></textarea>
          </div>
          <div>
            <label for="lang">Output language</label>
            <select id="lang">
              <option value="ko" selected>ko</option>
              <option value="en">en</option>
              <option value="ja">ja</option>
            </select>
          </div>
          <div>
            <label for="style">Style template</label>
            <select id="style">
              <option value="A" selected>A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </div>
          <div>
            <label for="maxCuts">Max image cuts (smoke)</label>
            <input id="maxCuts" type="number" min="1" max="9" step="1" value="2" />
          </div>
        </div>

        <div class="actions">
          <button id="promptBtn" type="button">Generate prompt preview</button>
          <button id="imageBtn" type="button">Generate images</button>
          <button id="sampleBtn" type="button">Fill sample</button>
        </div>

        <div id="status">Ready.</div>

        <div class="results" id="promptResults" hidden>
          <div class="box">
            <div class="box-head">Anchor Prompt</div>
            <pre id="anchorPrompt"></pre>
          </div>
          <div class="box">
            <div class="box-head">Plan JSON</div>
            <pre id="planJson"></pre>
          </div>
          <div class="cut-grid" id="cutGrid"></div>
        </div>

        <div class="results" id="imageResults" hidden>
          <div class="box">
            <div class="box-head">Anchor Image</div>
            <div class="img-card">
              <img id="anchorImage" alt="anchor image" />
              <div class="img-meta">Character anchor</div>
            </div>
          </div>
          <div class="box">
            <div class="box-head">9 Cuts</div>
            <div class="img-grid" id="imageGrid"></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const sourceText = document.getElementById("sourceText");
      const lang = document.getElementById("lang");
      const style = document.getElementById("style");
      const maxCuts = document.getElementById("maxCuts");
      const promptBtn = document.getElementById("promptBtn");
      const imageBtn = document.getElementById("imageBtn");
      const sampleBtn = document.getElementById("sampleBtn");
      const statusBox = document.getElementById("status");
      const promptResults = document.getElementById("promptResults");
      const imageResults = document.getElementById("imageResults");
      const anchorPrompt = document.getElementById("anchorPrompt");
      const planJson = document.getElementById("planJson");
      const cutGrid = document.getElementById("cutGrid");
      const anchorImage = document.getElementById("anchorImage");
      const imageGrid = document.getElementById("imageGrid");

      function setStatus(text, isError = false) {
        statusBox.textContent = text;
        statusBox.classList.toggle("error", isError);
      }

      function currentPayload() {
        let cuts = Number.parseInt(maxCuts.value || "2", 10);
        if (!Number.isFinite(cuts)) cuts = 2;
        cuts = Math.max(1, Math.min(9, cuts));
        return {
          source_text: sourceText.value.trim(),
          output_language: lang.value,
          style_template: style.value,
          max_image_cuts: cuts
        };
      }

      function validatePayload(payload) {
        if (!payload.source_text) {
          setStatus("source_text is required.", true);
          return false;
        }
        return true;
      }

      function setBusy(isBusy) {
        promptBtn.disabled = isBusy;
        imageBtn.disabled = isBusy;
        sampleBtn.disabled = isBusy;
      }

      sampleBtn.addEventListener("click", () => {
        sourceText.value = "비가 억수같이 쏟아지던 밤, 수연은 폐역 앞에서 낡은 열쇠를 주웠다.\\n그 열쇠를 쥐는 순간 오래 잠긴 문이 열리는 소리가 들렸다.\\n하지만 문은 보이지 않았고, 다음 날 도시 곳곳에 같은 열쇠 문양이 나타나기 시작했다.";
      });

      promptBtn.addEventListener("click", async () => {
        const payload = currentPayload();
        if (!validatePayload(payload)) return;

        setBusy(true);
        cutGrid.innerHTML = "";
        promptResults.hidden = true;
        setStatus("Generating prompt preview via Gemini text model...");

        try {
          const res = await fetch("/api/prompt-preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (!res.ok) {
            const detail = data && data.detail ? data.detail : "Request failed";
            throw new Error(detail);
          }

          anchorPrompt.textContent = data.anchor_prompt;
          planJson.textContent = JSON.stringify(data.plan, null, 2);

          const cuts = [...(data.cuts || [])].sort((a, b) => a.index - b.index);
          for (const cut of cuts) {
            const box = document.createElement("div");
            box.className = "box";

            const head = document.createElement("div");
            head.className = "box-head";
            head.textContent = "Cut " + cut.index + " prompt | refs: " + (cut.reference_inputs || []).join(", ");

            const pre = document.createElement("pre");
            pre.textContent = cut.prompt || "";

            box.appendChild(head);
            box.appendChild(pre);
            cutGrid.appendChild(box);
          }

          promptResults.hidden = false;
          setStatus("Done. Generated " + cuts.length + " cut prompts.");
        } catch (err) {
          setStatus(String(err.message || err), true);
        } finally {
          setBusy(false);
        }
      });

      imageBtn.addEventListener("click", async () => {
        const payload = currentPayload();
        if (!validatePayload(payload)) return;

        setBusy(true);
        imageGrid.innerHTML = "";
        imageResults.hidden = true;
        setStatus("Generating " + payload.max_image_cuts + " image cut(s) via /api/teaser...");

        try {
          const res = await fetch("/api/teaser", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (!res.ok) {
            const detail = data && data.detail ? data.detail : "Request failed";
            throw new Error(detail);
          }

          anchorImage.src = "data:image/png;base64," + data.character_anchor_image_base64;

          const cuts = [...(data.cuts || [])].sort((a, b) => a.index - b.index);
          for (const cut of cuts) {
            const card = document.createElement("div");
            card.className = "img-card";

            const img = document.createElement("img");
            img.alt = "cut-" + cut.index;
            img.src = "data:image/png;base64," + cut.image_base64;

            const meta = document.createElement("div");
            meta.className = "img-meta";
            meta.textContent = "Cut " + cut.index;

            card.appendChild(img);
            card.appendChild(meta);
            imageGrid.appendChild(card);
          }

          imageResults.hidden = false;
          setStatus("Done. Received " + cuts.length + " cut images.");
        } catch (err) {
          setStatus(String(err.message || err), true);
        } finally {
          setBusy(false);
        }
      });
    </script>
  </body>
</html>
"""
