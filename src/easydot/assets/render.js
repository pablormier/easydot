(async () => {
  const target = document.getElementById(__EASYDOT_CONTAINER_ID__);
  if (!target) {
    return;
  }
  const decode = (encoded) => {
    const binary = atob(encoded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  };
  const syncFrameHeight = () => {
    const frame = window.frameElement;
    if (!frame) return;
    try {
      frame.style.height = `${Math.ceil(target.scrollHeight)}px`;
    } catch (_err) {
      /* cross-origin frames reject the write; best-effort only */
    }
  };
  const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve));
  const statusMarkup = (message) =>
    `<div class="easydot-status" data-easydot-status><span class="easydot-spinner" aria-hidden="true"></span><span data-easydot-status-text>${message}</span></div>`;
  const showStatus = (message, state = "info") => {
    let status = target.querySelector("[data-easydot-status]");
    if (!status) {
      target.insertAdjacentHTML("beforeend", statusMarkup(message));
      status = target.querySelector("[data-easydot-status]");
    }
    const text = status.querySelector("[data-easydot-status-text]");
    if (text) {
      text.textContent = message;
    }
    status.classList.toggle("is-warning", state === "warning");
    syncFrameHeight();
  };
  const workerSource = `
    const loadGraphviz = async (moduleUrls) => {
      let lastError = null;
      for (const url of moduleUrls) {
        try {
          const mod = await import(url);
          const Graphviz = mod.Graphviz || (mod.default && mod.default.Graphviz) || mod.default;
          if (!Graphviz || !Graphviz.load) {
            throw new Error("Graphviz WASM module does not expose Graphviz.load()");
          }
          return Graphviz.load();
        } catch (error) {
          lastError = error;
        }
      }
      throw lastError || new Error("Unable to load Graphviz WASM module");
    };
    self.onmessage = async (event) => {
      try {
        const { moduleUrls, dot, format, engine } = event.data;
        const graphviz = await loadGraphviz(moduleUrls);
        const svg = graphviz.layout(dot, format, engine);
        self.postMessage({ ok: true, svg });
      } catch (error) {
        self.postMessage({ ok: false, error: String((error && error.message) || error) });
      }
    };
  `;
  const createRenderWorker = () => {
    if (typeof Worker === "undefined" || typeof Blob === "undefined" || typeof URL === "undefined") {
      throw new Error("Web Workers are unavailable");
    }
    const url = URL.createObjectURL(new Blob([workerSource], { type: "text/javascript" }));
    try {
      return new Worker(url, { type: "module" });
    } finally {
      URL.revokeObjectURL(url);
    }
  };
  try {
    const moduleUrls = __EASYDOT_MODULE_URLS__;
    const dot = decode("__EASYDOT_DOT_B64__");
    const format = decode("__EASYDOT_FORMAT_B64__");
    const engine = decode("__EASYDOT_ENGINE_B64__");
    const workerMode = __EASYDOT_WORKER_MODE__;
    const easydot = (globalThis.__easydot__ ||= {});
    const cache = (easydot.graphvizCache ||= new Map());
    const loadGraphviz = async () => {
      let lastError = null;
      for (const url of moduleUrls) {
        let pending = cache.get(url);
        if (!pending) {
          pending = (async () => {
            const mod = await import(url);
            const Graphviz = mod.Graphviz || (mod.default && mod.default.Graphviz) || mod.default;
            if (!Graphviz || !Graphviz.load) {
              throw new Error("Graphviz WASM module does not expose Graphviz.load()");
            }
            return Graphviz.load();
          })();
          cache.set(url, pending);
        }
        try {
          return await pending;
        } catch (error) {
          if (cache.get(url) === pending) {
            cache.delete(url);
          }
          lastError = error;
        }
      }
      throw lastError || new Error("Unable to load Graphviz WASM module");
    };
    const renderOnMainThread = async (message = "Rendering graph...", state = "info") => {
      showStatus(message, state);
      await nextFrame();
      const graphviz = await loadGraphviz();
      return graphviz.layout(dot, format, engine);
    };
    const renderInWorker = () =>
      new Promise((resolve, reject) => {
        const worker = createRenderWorker();
        worker.onmessage = (event) => {
          worker.terminate();
          const message = event.data;
          if (message && message.ok) {
            resolve(message.svg);
          } else {
            reject(new Error((message && message.error) || "Graphviz worker failed"));
          }
        };
        worker.onerror = (event) => {
          worker.terminate();
          reject(new Error(event.message || "Graphviz worker failed"));
        };
        worker.postMessage({ moduleUrls, dot, format, engine });
      });
    const renderDot = async () => {
      if (workerMode === "disabled") {
        return renderOnMainThread();
      }
      try {
        showStatus("Rendering graph...");
        return await renderInWorker();
      } catch (error) {
        if (workerMode === "require") {
          throw new Error(`Web Worker rendering was required but failed: ${error.message}`);
        }
        return renderOnMainThread(
          "Web Worker unavailable; rendering on main thread. Large graphs may freeze this output.",
          "warning",
        );
      }
    };
    const svg = await renderDot();
    __EASYDOT_SVG_INSTALL_JS__

    const fit = __EASYDOT_FIT__;
    const scale = __EASYDOT_SCALE__;
    const svgEl = target.querySelector(":scope > svg");
    if (svgEl) {
      const vb = svgEl.viewBox && svgEl.viewBox.baseVal;
      const width = svgEl.width && svgEl.width.baseVal;
      const height = svgEl.height && svgEl.height.baseVal;
      const rect = svgEl.getBoundingClientRect();
      const naturalW = (width && width.value) || (vb && vb.width) || rect.width || 1;
      const naturalH = (height && height.value) || (vb && vb.height) || rect.height || 1;
      target.style.setProperty("--easydot-nat-w", String(naturalW));
      target.style.setProperty("--easydot-nat-h", String(naturalH));
      target.style.setProperty("--easydot-scale", String(scale));
      if (fit === "none" && scale !== 1) {
        target.classList.add("easydot-scaled");
      }
    }
    __EASYDOT_TOOLBAR_SETUP_JS__

    const isViewportFit = fit === "vertical" || fit === "both";
    if (!isViewportFit) {
      syncFrameHeight();
      if (svgEl && typeof ResizeObserver !== "undefined") {
        new ResizeObserver(syncFrameHeight).observe(svgEl);
      }
    }
  } catch (error) {
    target.innerHTML = "<pre style='white-space:pre-wrap;color:#b00020'>Graph rendering failed: "
      + String(error) + "</pre>";
    syncFrameHeight();
  }
})();
