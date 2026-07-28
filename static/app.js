(() => {
  const $ = (id) => document.getElementById(id);

  const canvas = $("canvas");
  const ctx = canvas.getContext("2d");
  const fileInput = $("file");
  const detectStyle = $("detectStyle");
  const detectBtn = $("detectBtn");
  const urlInput = $("url");
  const loadUrlBtn = $("loadUrlBtn");
  const sampleBtn = $("sampleBtn");
  const clearBtn = $("clearBtn");
  const generateBtn = $("generateBtn");
  const copyBtn = $("copyBtn");
  const copyLuaBtn = $("copyLuaBtn");
  const pointsList = $("pointsList");
  const pointCount = $("pointCount");
  const output = $("output");
  const luaOut = $("luaOut");
  const statusEl = $("status");
  const frameControls = $("frameControls");
  const frameSlider = $("frameSlider");
  const frameLabel = $("frameLabel");

  let points = [];
  let image = null;
  let frameDataUrls = [];
  let activeFrameIndex = 0;

  function setStatus(text, isError = false) {
    statusEl.textContent = text;
    statusEl.className = isError ? "status error" : "status";
  }

  async function jsonFetch(url, opts) {
    const resp = await fetch(url, opts);
    const data = await resp.json();
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || `Request failed: ${resp.status}`);
    }
    return data;
  }

  function draw() {
    if (!image) {
      ctx.fillStyle = "#0a0d11";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      return;
    }
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    ctx.drawImage(image, 0, 0);
    points.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fillStyle = i === 0 ? "#5dcea5" : "#3d8bfd";
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.fillStyle = "#fff";
      ctx.font = "12px sans-serif";
      ctx.fillText(String(i + 1), p.x + 8, p.y - 8);
      if (i > 0) {
        const prev = points[i - 1];
        ctx.beginPath();
        ctx.moveTo(prev.x, prev.y);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = "rgba(61,139,253,0.55)";
        ctx.stroke();
      }
    });
  }

  function renderPoints() {
    pointCount.textContent = String(points.length);
    pointsList.innerHTML = points
      .map((p, i) => `<li>#${i + 1}: (${Math.round(p.x)}, ${Math.round(p.y)})</li>`)
      .join("");
    draw();
  }

  function showFrame(index) {
    if (!frameDataUrls.length) return;
    activeFrameIndex = Math.max(0, Math.min(index, frameDataUrls.length - 1));
    frameSlider.value = String(activeFrameIndex);
    frameLabel.textContent = `${activeFrameIndex + 1}/${frameDataUrls.length}`;
    const img = new Image();
    img.onload = () => {
      image = img;
      draw();
    };
    img.src = frameDataUrls[activeFrameIndex];
  }

  function applyDetected(data, includeSuggested) {
    frameDataUrls = Array.isArray(data.frame_data_urls) && data.frame_data_urls.length
      ? data.frame_data_urls
      : [data.preview_data_url];
    activeFrameIndex = Number.isInteger(data.recommended_frame_index)
      ? data.recommended_frame_index
      : Math.max(0, frameDataUrls.length - 1);

    const multi = frameDataUrls.length > 1;
    frameControls.classList.toggle("hidden", !multi);
    frameSlider.min = "0";
    frameSlider.max = String(Math.max(0, frameDataUrls.length - 1));

    if (includeSuggested) points = (data.suggested_points || []).map((p) => ({ x: p.x, y: p.y }));
    showFrame(activeFrameIndex);
    renderPoints();
    setStatus(
      includeSuggested
        ? `Loaded. ${points.length} suggested points (${data.detect_style}). Fix order if needed.`
        : "Loaded. Click to mark points in shot order."
    );
  }

  async function detectFromFile(includeSuggested) {
    const file = fileInput.files && fileInput.files[0];
    if (!file) throw new Error("Select an image or GIF first.");
    const form = new FormData();
    form.append("spray_file", file);
    form.append("detect_style", detectStyle.value);
    const data = await jsonFetch("/api/detect", { method: "POST", body: form });
    applyDetected(data, includeSuggested);
  }

  async function detectFromUrl(url, includeSuggested) {
    const data = await jsonFetch("/api/detect-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_url: url, detect_style: detectStyle.value }),
    });
    applyDetected(data, includeSuggested);
  }

  function canvasCoords(evt) {
    const rect = canvas.getBoundingClientRect();
    const sx = canvas.width / rect.width;
    const sy = canvas.height / rect.height;
    return {
      x: (evt.clientX - rect.left) * sx,
      y: (evt.clientY - rect.top) * sy,
    };
  }

  canvas.addEventListener("click", (evt) => {
    if (!image) return;
    const { x, y } = canvasCoords(evt);
    points.push({ x, y });
    renderPoints();
  });

  canvas.addEventListener("contextmenu", (evt) => {
    evt.preventDefault();
    if (!points.length) return;
    points.pop();
    renderPoints();
  });

  clearBtn.addEventListener("click", () => {
    points = [];
    output.value = "";
    luaOut.value = "";
    renderPoints();
    setStatus("Points cleared.");
  });

  frameSlider.addEventListener("input", () => {
    showFrame(parseInt(frameSlider.value, 10) || 0);
  });

  fileInput.addEventListener("change", async () => {
    try {
      await detectFromFile(false);
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  detectBtn.addEventListener("click", async () => {
    try {
      if (fileInput.files && fileInput.files[0]) {
        await detectFromFile(true);
        return;
      }
      const url = (urlInput.value || "").trim();
      if (url) {
        await detectFromUrl(url, true);
        return;
      }
      throw new Error("Select a file or paste a URL first.");
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  loadUrlBtn.addEventListener("click", async () => {
    try {
      const url = (urlInput.value || "").trim();
      if (!url) throw new Error("Paste a URL first.");
      await detectFromUrl(url, true);
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  sampleBtn.addEventListener("click", async () => {
    try {
      detectStyle.value = "gif";
      const url = `${window.location.origin}/samples/weapon_ak47.gif`;
      urlInput.value = url;
      await detectFromUrl(url, true);
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  async function generate() {
    if (points.length < 2) throw new Error("Add at least 2 points.");
    const data = await jsonFetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        points,
        delay_ms: parseInt($("delayMs").value, 10) || 90,
        scale_x: parseFloat($("scaleX").value) || 1,
        scale_y: parseFloat($("scaleY").value) || 1,
        invert_x: $("invertX").checked,
        invert_y: $("invertY").checked,
      }),
    });
    output.value = data.pattern_text || "";
    luaOut.value = data.lua_text || "";
    setStatus(`Generated ${data.steps_count} steps.`);
    return data;
  }

  generateBtn.addEventListener("click", async () => {
    try {
      await generate();
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  copyBtn.addEventListener("click", async () => {
    try {
      if (!output.value.trim()) await generate();
      await navigator.clipboard.writeText(output.value);
      setStatus("CSV copied.");
    } catch (err) {
      setStatus(err.message || "Copy failed.", true);
    }
  });

  copyLuaBtn.addEventListener("click", async () => {
    try {
      if (!luaOut.value.trim()) await generate();
      await navigator.clipboard.writeText(luaOut.value);
      setStatus("Lua sketch copied.");
    } catch (err) {
      setStatus(err.message || "Copy failed.", true);
    }
  });

  renderPoints();
})();
