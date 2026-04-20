"""HTML helpers for browser-side DOT rendering."""

from __future__ import annotations

import base64
import html as html_lib
import json
import sys
import uuid

from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._server import asset_urls

DEFAULT_CDN_URL = f"https://cdn.jsdelivr.net/npm/{UPSTREAM_PACKAGE}@{UPSTREAM_VERSION}/dist/index.min.js"


def _b64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _js_literal(value: object) -> str:
    return json.dumps(value).replace("</", "<\\/")


_FIT_MODES = ("none", "horizontal", "vertical", "both")
_DEFAULT_IFRAME_HEIGHT = "220px"


def _normalize_fit(value: bool | str) -> str:
    if isinstance(value, bool):
        return "both" if value else "none"
    if isinstance(value, str) and value in _FIT_MODES:
        return value
    raise ValueError(
        "fit must be True, False, or one of 'horizontal', 'vertical', 'both', 'none'; "
        f"got {value!r}"
    )


def _module_urls(source: str) -> list[str]:
    if source == "cdn":
        return [DEFAULT_CDN_URL]
    if source == "local":
        return [asset_urls()["js"]]
    if source != "auto":
        raise ValueError("source must be 'auto', 'local', or 'cdn'")

    try:
        return [asset_urls()["js"], DEFAULT_CDN_URL]
    except OSError:
        return [DEFAULT_CDN_URL]


_COPY_ICON = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="9" y="9" width="11" height="11" rx="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
)
_DOWNLOAD_ICON = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
    '<polyline points="7 10 12 15 17 10"/>'
    '<line x1="12" y1="15" x2="12" y2="3"/></svg>'
)
_CHECK_ICON = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<polyline points="20 6 9 17 4 12"/></svg>'
)


def _toolbar_stylesheet(attr_id: str) -> str:
    return (
        f"#{attr_id} .easydot-toolbar{{"
        "position:sticky;top:0;left:0;z-index:1;"
        "display:flex;justify-content:flex-end;gap:2px;padding:3px 4px;"
        "background:rgba(255,255,255,0.78);backdrop-filter:blur(4px);"
        "-webkit-backdrop-filter:blur(4px);"
        "opacity:0.4;transition:opacity 150ms ease-in-out;"
        "box-sizing:border-box;width:100%;"
        "}"
        f"#{attr_id}:hover .easydot-toolbar,"
        f"#{attr_id} .easydot-toolbar:focus-within{{opacity:1}}"
        f"#{attr_id} .easydot-toolbar button{{"
        "background:transparent;border:0;border-radius:4px;padding:3px;"
        "margin:0;cursor:pointer;color:#6b6b6b;line-height:0;"
        "transition:color 120ms ease-in-out,background-color 120ms ease-in-out;"
        "}"
        f"#{attr_id} .easydot-toolbar button:hover{{color:#111;background:rgba(0,0,0,0.06)}}"
        f"#{attr_id} .easydot-toolbar button:focus-visible{{"
        "outline:2px solid rgba(0,95,204,0.5);outline-offset:1px;"
        "}"
        f"#{attr_id} .easydot-toolbar button.is-success{{color:#1a7f37}}"
        f"#{attr_id} .easydot-toolbar button.is-error{{color:#b00020}}"
    )


def html(
    dot: str,
    *,
    engine: str = "dot",
    format: str = "svg",
    container_id: str | None = None,
    source: str = "auto",
    fit: bool | str = False,
    scale: float = 1.0,
    toolbar: bool = True,
) -> str:
    """Return browser HTML that renders DOT with the bundled Graphviz WASM module."""

    if container_id is None:
        container_id = f"easydot-{uuid.uuid4().hex}"

    fit_mode = _normalize_fit(fit)
    dot_b64 = _b64_text(dot)
    module_urls = _js_literal(_module_urls(source))
    safe_engine = _b64_text(engine)
    safe_format = _b64_text(format)
    attr_id = html_lib.escape(container_id, quote=True)
    js_id = _js_literal(container_id)
    js_fit = _js_literal(fit_mode)
    js_scale = _js_literal(float(scale))
    js_format = _js_literal(format)
    skip_frame_resize = fit_mode in ("vertical", "both")
    js_skip_frame_resize = _js_literal(skip_frame_resize)

    body_style = "html,body{margin:0;padding:0}"
    container_style = "overflow:auto"
    if fit_mode == "vertical":
        body_style = "html,body{margin:0;padding:0;height:100%;overflow:hidden}"
        container_style = "height:100%;overflow-x:auto;overflow-y:hidden;box-sizing:border-box"
    elif fit_mode == "both":
        body_style = "html,body{margin:0;padding:0;height:100%;overflow:hidden}"
        container_style = "height:100%;overflow:hidden;box-sizing:border-box"
    toolbar_markup = ""
    svg_install_js = "target.innerHTML = svg;"
    toolbar_setup_js = ""
    resize_toolbar_js = ""
    resize_toolbar_extra = "0"
    fit_toolbar_query = "null"
    if toolbar:
        fit_toolbar_query = "target.querySelector(':scope > [data-easydot-toolbar]')"
        resize_toolbar_js = (
            "\n      const toolbarEl = target.querySelector(':scope > [data-easydot-toolbar]');"
            "\n      const toolbarExtra = toolbarEl ? Math.ceil(toolbarEl.getBoundingClientRect().height) : 0;"
        )
        resize_toolbar_extra = "toolbarExtra"
        toolbar_markup = (
            f"<style>{_toolbar_stylesheet(attr_id)}</style>"
            '<div class="easydot-toolbar" data-easydot-toolbar>'
            f'<button type="button" data-easydot-copy aria-label="Copy SVG to clipboard" title="Copy SVG">{_COPY_ICON}</button>'
            f'<button type="button" data-easydot-download aria-label="Download SVG" title="Download SVG">{_DOWNLOAD_ICON}</button>'
            "</div>"
        )
        svg_install_js = (
            "const toolbarEl = target.querySelector('[data-easydot-toolbar]');"
            "target.querySelectorAll(':scope > :not([data-easydot-toolbar]):not(style)').forEach((node) => node.remove());"
            "target.insertAdjacentHTML('beforeend', svg);"
        )
        toolbar_setup_js = f"""
    if (toolbarEl) {{
      const format = {js_format};
      const mime = format === "svg" ? "image/svg+xml;charset=utf-8" : "text/plain;charset=utf-8";
      const filename = `graph.${{format}}`;
      const checkIcon = {_js_literal(_CHECK_ICON)};
      const flash = (btn, state) => {{
        const original = btn.dataset.originalIcon ||= btn.innerHTML;
        btn.classList.remove("is-success", "is-error");
        btn.classList.add(state === "error" ? "is-error" : "is-success");
        if (state !== "error") {{
          btn.innerHTML = checkIcon;
        }}
        clearTimeout(btn.dataset.flashTimer);
        btn.dataset.flashTimer = setTimeout(() => {{
          btn.innerHTML = btn.dataset.originalIcon;
          btn.classList.remove("is-success", "is-error");
        }}, 1100);
      }};
      const copyBtn = toolbarEl.querySelector("[data-easydot-copy]");
      const downloadBtn = toolbarEl.querySelector("[data-easydot-download]");
      if (copyBtn) {{
        copyBtn.addEventListener("click", async () => {{
          try {{
            await navigator.clipboard.writeText(svg);
            flash(copyBtn, "success");
          }} catch (_err) {{
            flash(copyBtn, "error");
          }}
        }});
      }}
      if (downloadBtn) {{
        downloadBtn.addEventListener("click", () => {{
          try {{
            const blob = new Blob([svg], {{ type: mime }});
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            setTimeout(() => URL.revokeObjectURL(url), 0);
            flash(downloadBtn, "success");
          }} catch (_err) {{
            flash(downloadBtn, "error");
          }}
        }});
      }}
    }}"""

    return f"""
<style>{body_style}</style>
<div id="{attr_id}" style="{container_style}">{toolbar_markup}</div>
<script type="module">
(async () => {{
  const target = document.getElementById({js_id});
  if (!target) {{
    return;
  }}
  const decode = (encoded) => {{
    const binary = atob(encoded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  }};
  const resizeFrameToContent = () => {{
    try {{
      const height = Math.ceil(target.scrollHeight);
      if (window.frameElement) {{
        window.frameElement.style.height = `${{height}}px`;
      }}
    }} catch (_err) {{
      /* best effort only */
    }}
  }};
  try {{
    const moduleUrls = {module_urls};
    const cache = (globalThis.__easydotGraphvizCache__ ||= new Map());
    const loadGraphviz = async () => {{
      let lastError = null;
      for (const url of moduleUrls) {{
        let pending = cache.get(url);
        if (!pending) {{
          pending = (async () => {{
            const mod = await import(url);
            const Graphviz = mod.Graphviz || (mod.default && mod.default.Graphviz) || mod.default;
            if (!Graphviz || !Graphviz.load) {{
              throw new Error("Graphviz WASM module does not expose Graphviz.load()");
            }}
            return Graphviz.load();
          }})();
          cache.set(url, pending);
        }}
        try {{
          return await pending;
        }} catch (error) {{
          if (cache.get(url) === pending) {{
            cache.delete(url);
          }}
          lastError = error;
        }}
      }}
      throw lastError || new Error("Unable to load Graphviz WASM module");
    }};
    const graphviz = await loadGraphviz();
    const svg = await graphviz.layout(decode("{dot_b64}"), decode("{safe_format}"), decode("{safe_engine}"));
    {svg_install_js}
    const fit = {js_fit};
    const scale = {js_scale};
    const skipFrameResize = {js_skip_frame_resize};
    const svgEl = target.querySelector(":scope > svg");
    if (svgEl) {{
      const fitToolbarEl = {fit_toolbar_query};
      const toolbarExtra = fitToolbarEl ? Math.ceil(fitToolbarEl.getBoundingClientRect().height) : 0;
      if (fit === "horizontal") {{
        const naturalW = svgEl.getBoundingClientRect().width;
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = "100%";
        svgEl.style.height = "auto";
        svgEl.style.maxWidth = `${{Math.ceil(naturalW * scale)}}px`;
      }} else if (fit === "vertical") {{
        const rect = svgEl.getBoundingClientRect();
        const avail = Math.max(1, document.documentElement.clientHeight - toolbarExtra);
        const targetH = Math.min(rect.height * scale, avail);
        const k = rect.height > 0 ? targetH / rect.height : 1;
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.height = `${{Math.floor(targetH)}}px`;
        svgEl.style.width = `${{Math.floor(rect.width * k)}}px`;
      }} else if (fit === "both") {{
        const rect = svgEl.getBoundingClientRect();
        const availW = Math.max(1, target.clientWidth);
        const availH = Math.max(1, document.documentElement.clientHeight - toolbarExtra);
        const k = Math.min(scale, availW / rect.width, availH / rect.height);
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = `${{Math.floor(rect.width * k)}}px`;
        svgEl.style.height = `${{Math.floor(rect.height * k)}}px`;
      }} else if (scale !== 1) {{
        const rect = svgEl.getBoundingClientRect();
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.display = "block";
        svgEl.style.width = `${{Math.ceil(rect.width * scale)}}px`;
        svgEl.style.height = `${{Math.ceil(rect.height * scale)}}px`;
      }}
    }}{toolbar_setup_js}
    if (!skipFrameResize) {{
      resizeFrameToContent();
      requestAnimationFrame(resizeFrameToContent);
      setTimeout(resizeFrameToContent, 50);
    }}
  }} catch (error) {{
    target.innerHTML = "<pre style='white-space:pre-wrap;color:#b00020'>Graph rendering failed: "
      + String(error) + "</pre>";
    resizeFrameToContent();
  }}
}})();
</script>
"""


class DotDisplay:
    """Rich display wrapper for DOT graphs."""

    def __init__(
        self,
        dot: str,
        *,
        engine: str = "dot",
        format: str = "svg",
        iframe_height: str | None = None,
        source: str = "auto",
        fit: bool | str = False,
        scale: float = 1.0,
        iframe: bool = True,
        toolbar: bool = True,
    ) -> None:
        self.dot = dot
        self.engine = engine
        self.format = format
        self.iframe_height = iframe_height if iframe_height is not None else _DEFAULT_IFRAME_HEIGHT
        self.source = source
        self.fit = fit
        self.scale = scale
        self.iframe = iframe
        self.toolbar = toolbar

    def _body_html(self) -> str:
        return html(
            self.dot,
            engine=self.engine,
            format=self.format,
            source=self.source,
            fit=self.fit,
            scale=self.scale,
            toolbar=self.toolbar,
        )

    def _iframe_html(self) -> str:
        escaped = html_lib.escape(self._body_html(), quote=True)
        return f"<iframe srcdoc='{escaped}' width='100%' height='{self.iframe_height}' frameborder='0'></iframe>"

    def _mime_(self) -> tuple[str, str]:
        if not self.iframe:
            return "text/html", self._body_html()

        try:
            from marimo._output.formatting import iframe
        except ImportError:
            iframe = None

        if iframe is not None:
            frame = iframe(self._body_html(), height=self.iframe_height)
            frame_mime = getattr(frame, "_mime_", None)
            if callable(frame_mime):
                mime_type, payload = frame_mime()
                if mime_type == "text/html" and isinstance(payload, str):
                    return mime_type, payload
            payload = getattr(frame, "html", None)
            if isinstance(payload, str):
                return "text/html", payload

        if "IPython" in sys.modules:
            return "text/html", self._iframe_html()
        return "text/html", self._body_html()

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, str]:
        """Return a Jupyter MIME bundle for frontends that prefer it."""

        mime_type, payload = self._mime_()
        return {mime_type: payload}

    def _ipython_display_(self) -> None:
        """Publish HTML directly when IPython's display hook is available."""

        try:
            from IPython.display import display_html
        except ImportError:
            return

        payload = self._iframe_html() if self.iframe else self._body_html()
        display_html(payload, raw=True)

    def _repr_html_(self) -> str:
        if self.iframe and "IPython" in sys.modules:
            return self._iframe_html()
        return self._body_html()

    def __repr__(self) -> str:
        return self.dot


def display(
    dot: str,
    *,
    engine: str = "dot",
    format: str = "svg",
    iframe_height: str | None = None,
    source: str = "auto",
    fit: bool | str = False,
    scale: float = 1.0,
    iframe: bool = True,
    toolbar: bool = True,
) -> DotDisplay:
    """Return a rich display object for a DOT graph."""

    return DotDisplay(
        dot,
        engine=engine,
        format=format,
        iframe_height=iframe_height,
        source=source,
        fit=fit,
        scale=scale,
        iframe=iframe,
        toolbar=toolbar,
    )
