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
  const resizeFrameToContent = () => {
    try {
      const height = Math.ceil(target.scrollHeight);
      if (window.frameElement) {
        window.frameElement.style.height = `${height}px`;
      }
    } catch (_err) {
      /* best effort only */
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
    const skipFrameResize = __EASYDOT_SKIP_FRAME_RESIZE__;

    const applyFit = () => {
      const svgEl = target.querySelector(":scope > svg");
      if (!svgEl) {
        return;
      }
      const fitToolbarEl = __EASYDOT_FIT_TOOLBAR_QUERY__;
      const toolbarExtra = fitToolbarEl ? Math.ceil(fitToolbarEl.getBoundingClientRect().height) : 0;

      let naturalW = parseFloat(svgEl.dataset.easydotNaturalW);
      let naturalH = parseFloat(svgEl.dataset.easydotNaturalH);
      if (!naturalW || !naturalH) {
        const rect = svgEl.getBoundingClientRect();
        naturalW = rect.width;
        naturalH = rect.height;
        svgEl.dataset.easydotNaturalW = String(naturalW);
        svgEl.dataset.easydotNaturalH = String(naturalH);
      }

      if (fit === "horizontal") {
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = "100%";
        svgEl.style.height = "auto";
        svgEl.style.maxWidth = `${Math.ceil(naturalW * scale)}px`;
      } else if (fit === "vertical") {
        const avail = Math.max(1, document.documentElement.clientHeight - toolbarExtra);
        const targetH = Math.min(naturalH * scale, avail);
        const k = naturalH > 0 ? targetH / naturalH : 1;
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.height = `${Math.floor(targetH)}px`;
        svgEl.style.width = `${Math.floor(naturalW * k)}px`;
      } else if (fit === "both") {
        const availW = Math.max(1, target.clientWidth);
        const availH = Math.max(1, document.documentElement.clientHeight - toolbarExtra);
        const k = Math.min(scale, availW / naturalW, availH / naturalH);
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = `${Math.floor(naturalW * k)}px`;
        svgEl.style.height = `${Math.floor(naturalH * k)}px`;
      } else if (scale !== 1) {
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = `${Math.ceil(naturalW * scale)}px`;
        svgEl.style.height = `${Math.ceil(naturalH * scale)}px`;
      }
    };

    const applyLayout = () => {
      applyFit();
      if (!skipFrameResize) {
        resizeFrameToContent();
      }
    };

    applyFit();
    let resizeRaf = null;
    window.addEventListener("resize", () => {
      if (resizeRaf) {
        cancelAnimationFrame(resizeRaf);
      }
      resizeRaf = requestAnimationFrame(applyLayout);
    });

    __EASYDOT_TOOLBAR_SETUP_JS__
    if (!skipFrameResize) {
      resizeFrameToContent();
      requestAnimationFrame(resizeFrameToContent);
      setTimeout(resizeFrameToContent, 50);
    }
  } catch (error) {
    target.innerHTML = "<pre style='white-space:pre-wrap;color:#b00020'>Graph rendering failed: "
      + String(error) + "</pre>";
    resizeFrameToContent();
  }
})();
