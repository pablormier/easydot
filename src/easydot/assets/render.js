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
  __EASYDOT_FIT_LIFECYCLE_JS__
  const initialFitControls = setupEasydotFit(target, "none", 1, false);
  const syncFrameHeight = initialFitControls.syncFrameHeight;
  const nextFrame = () => new Promise((resolve) => requestAnimationFrame(resolve));
  const showSpinner = __EASYDOT_SHOW_SPINNER__;
  const workerMode = __EASYDOT_WORKER_MODE__;
  const glyphs = __EASYDOT_GLYPHS__;
  const stopIcon = __EASYDOT_STOP_ICON__;
  const composeSvgGlyphs = (source, glyphAssets) => {
    if (!Object.keys(glyphAssets).length) {
      return source;
    }
    const document = new DOMParser().parseFromString(source, "image/svg+xml");
    if (document.querySelector("parsererror")) {
      throw new Error("Graphviz returned invalid SVG");
    }
    const svgNamespace = "http://www.w3.org/2000/svg";
    const xlinkNamespace = "http://www.w3.org/1999/xlink";
    const numberPattern = /[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g;
    for (const [nodeId, href] of Object.entries(glyphAssets)) {
      const nodes = Array.from(document.getElementsByTagName("g")).filter(
        (element) =>
          element.getAttribute("id") === nodeId &&
          element.getAttribute("class")?.split(/\s+/).includes("node"),
      );
      if (!nodes.length) {
        throw new Error(`No Graphviz node with id ${JSON.stringify(nodeId)} was found`);
      }
      if (nodes.length > 1) {
        throw new Error(`Multiple Graphviz nodes have id ${JSON.stringify(nodeId)}`);
      }
      const node = nodes[0];
      const shape = Array.from(node.children).find(
        (element) => element.localName === "ellipse" || element.localName === "polygon",
      );
      if (!shape) {
        throw new Error(
          `Unsupported proxy geometry for node id ${JSON.stringify(nodeId)}; use shape=ellipse or shape=box`,
        );
      }
      let x;
      let y;
      let width;
      let height;
      if (shape.localName === "ellipse") {
        const cx = Number(shape.getAttribute("cx"));
        const cy = Number(shape.getAttribute("cy"));
        const rx = Number(shape.getAttribute("rx"));
        const ry = Number(shape.getAttribute("ry"));
        if (![cx, cy, rx, ry].every(Number.isFinite) || rx <= 0 || ry <= 0) {
          throw new Error(`Unsupported proxy geometry for node id ${JSON.stringify(nodeId)}`);
        }
        [x, y, width, height] = [cx - rx, cy - ry, rx * 2, ry * 2];
      } else {
        const values = (shape.getAttribute("points").match(numberPattern) || []).map(Number);
        if (values.length < 8 || values.length % 2) {
          throw new Error(
            `Unsupported proxy geometry for node id ${JSON.stringify(nodeId)}; expected a rectangular box`,
          );
        }
        const points = [];
        for (let index = 0; index < values.length; index += 2) {
          points.push([values[index], values[index + 1]]);
        }
        const first = points[0];
        const last = points[points.length - 1];
        if (first[0] === last[0] && first[1] === last[1]) {
          points.pop();
        }
        const unique = new Map(points.map((point) => [`${point[0]},${point[1]}`, point]));
        const vertices = Array.from(unique.values());
        const xs = vertices.map((point) => point[0]);
        const ys = vertices.map((point) => point[1]);
        x = Math.min(...xs);
        y = Math.min(...ys);
        width = Math.max(...xs) - x;
        height = Math.max(...ys) - y;
        const corners = new Set([
          `${x},${y}`,
          `${x},${y + height}`,
          `${x + width},${y}`,
          `${x + width},${y + height}`,
        ]);
        const rectangle =
          vertices.length === 4 &&
          width > 0 &&
          height > 0 &&
          vertices.every((point) => corners.has(`${point[0]},${point[1]}`));
        if (!rectangle) {
          throw new Error(
            `Unsupported proxy geometry for node id ${JSON.stringify(nodeId)}; expected a rectangular box`,
          );
        }
      }
      const image = document.createElementNS(svgNamespace, "image");
      image.setAttribute("x", String(x));
      image.setAttribute("y", String(y));
      image.setAttribute("width", String(width));
      image.setAttribute("height", String(height));
      image.setAttribute("preserveAspectRatio", "none");
      image.setAttribute("href", href);
      image.setAttributeNS(xlinkNamespace, "xlink:href", href);
      shape.after(image);
    }
    return new XMLSerializer().serializeToString(document.documentElement);
  };
  const statusMarkup = (message, cancellable = false) =>
    `<div class="easydot-status" data-easydot-status>${
      showSpinner ? '<span class="easydot-spinner" aria-hidden="true"></span>' : ""
    }<span data-easydot-status-text>${message}</span>${
      cancellable
        ? `<button type="button" class="easydot-stop" data-easydot-stop aria-label="Cancel rendering" title="Cancel rendering">${stopIcon}</button>`
        : ""
    }</div>`;
  const showStatus = (message, state = "info", cancellable = false) => {
    let status = target.querySelector("[data-easydot-status]");
    if (!status) {
      target.insertAdjacentHTML("beforeend", statusMarkup(message, cancellable));
      status = target.querySelector("[data-easydot-status]");
    } else {
      const next = document.createElement("div");
      next.innerHTML = statusMarkup(message, cancellable);
      status.replaceWith(next.firstElementChild);
      status = target.querySelector("[data-easydot-status]");
    }
    const text = status.querySelector("[data-easydot-status-text]");
    if (text) {
      text.textContent = message;
    }
    status.classList.toggle("is-warning", state === "warning");
    syncFrameHeight();
  };
  const removeStatus = () => {
    target.querySelectorAll("[data-easydot-status]").forEach((el) => el.remove());
    syncFrameHeight();
  };
  const showCancelled = () => {
    const status = target.querySelector("[data-easydot-status]");
    if (status) {
      status.innerHTML = '<span data-easydot-status-text>Rendering cancelled.</span>';
    } else {
      target.insertAdjacentHTML("beforeend", '<div class="easydot-status" data-easydot-status"><span data-easydot-status-text>Rendering cancelled.</span></div>');
    }
    syncFrameHeight();
  };
  const abortController = new AbortController();
  const { signal } = abortController;
  const onStopClick = () => {
    abortController.abort();
  };
  target.addEventListener("click", (e) => {
    if (e.target.closest("[data-easydot-stop]")) {
      onStopClick();
    }
  });
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
    if (signal.aborted) {
      showCancelled();
      return;
    }
    const moduleUrls = __EASYDOT_MODULE_URLS__;
    const dot = decode("__EASYDOT_DOT_B64__");
    const format = decode("__EASYDOT_FORMAT_B64__");
    const engine = decode("__EASYDOT_ENGINE_B64__");
    const easydot = (globalThis.__easydot__ ||= {});
    const cache = (easydot.graphvizCache ||= new Map());
    const loadGraphviz = async () => {
      let lastError = null;
      for (const url of moduleUrls) {
        if (signal.aborted) {
          throw new DOMException("Rendering cancelled.", "AbortError");
        }
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
      if (signal.aborted) {
        throw new DOMException("Rendering cancelled.", "AbortError");
      }
      showStatus(message, state, false);
      await nextFrame();
      const graphviz = await loadGraphviz();
      if (signal.aborted) {
        throw new DOMException("Rendering cancelled.", "AbortError");
      }
      return await graphviz.layout(dot, format, engine);
    };
    const renderInWorker = () =>
      new Promise((resolve, reject) => {
        const worker = createRenderWorker();
        const onAbort = () => {
          worker.terminate();
          reject(new DOMException("Rendering cancelled.", "AbortError"));
        };
        if (signal.aborted) {
          worker.terminate();
          reject(new DOMException("Rendering cancelled.", "AbortError"));
          return;
        }
        signal.addEventListener("abort", onAbort);
        worker.onmessage = (event) => {
          signal.removeEventListener("abort", onAbort);
          worker.terminate();
          const message = event.data;
          if (message && message.ok) {
            resolve(message.svg);
          } else {
            reject(new Error((message && message.error) || "Graphviz worker failed"));
          }
        };
        worker.onerror = (event) => {
          signal.removeEventListener("abort", onAbort);
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
        showStatus("Rendering graph...", "info", true);
        return await renderInWorker();
      } catch (error) {
        if (error && error.name === "AbortError") {
          throw error;
        }
        if (workerMode === "require") {
          throw new Error(`Web Worker rendering was required but failed: ${error.message}`);
        }
        return renderOnMainThread(
          "Web Worker unavailable; rendering on main thread. Large graphs may freeze this output.",
          "warning",
        );
      }
    };
    let svg = await renderDot();
    if (signal.aborted) {
      return;
    }
    svg = composeSvgGlyphs(svg, glyphs);
    removeStatus();
    __EASYDOT_SVG_INSTALL_JS__

    const fit = __EASYDOT_FIT__;
    const scale = __EASYDOT_SCALE__;
    setupEasydotFit(target, fit, scale);
    __EASYDOT_TOOLBAR_SETUP_JS__
  } catch (error) {
    if (error && error.name === "AbortError") {
      showCancelled();
      return;
    }
    target.innerHTML = "<pre style='white-space:pre-wrap;color:#b00020'>Graph rendering failed: "
      + String(error) + "</pre>";
    syncFrameHeight();
  }
})();
