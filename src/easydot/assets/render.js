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
  try {
    const moduleUrls = __EASYDOT_MODULE_URLS__;
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
    const graphviz = await loadGraphviz();
    const svg = await graphviz.layout(
      decode("__EASYDOT_DOT_B64__"),
      decode("__EASYDOT_FORMAT_B64__"),
      decode("__EASYDOT_ENGINE_B64__"),
    );
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
