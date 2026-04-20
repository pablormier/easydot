"""HTML helpers for browser-side DOT rendering."""

from __future__ import annotations

import base64
import html as html_lib
import json
import os
import sys
import uuid
from importlib.resources import files

from easydot._icons import CHECK_ICON, COPY_ICON, DOWNLOAD_ICON
from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._server import asset_urls

DEFAULT_CDN_URL = f"https://cdn.jsdelivr.net/npm/{UPSTREAM_PACKAGE}@{UPSTREAM_VERSION}/dist/index.min.js"
SOURCE_ENV_VAR = "EASYDOT_SOURCE"
IFRAME_MODE_ENV_VAR = "EASYDOT_IFRAME_MODE"
_ASSET_PACKAGE = "easydot.assets"
_RENDER_TEMPLATE = files(_ASSET_PACKAGE).joinpath("render.js").read_text(encoding="utf-8")


def _b64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _js_literal(value: object) -> str:
    return json.dumps(value).replace("</", "<\\/")


_FIT_MODES = ("none", "horizontal", "vertical", "both")


def _normalize_fit(value: bool | str) -> str:
    if isinstance(value, bool):
        return "both" if value else "none"
    if isinstance(value, str) and value in _FIT_MODES:
        return value
    raise ValueError(
        "fit must be True, False, or one of 'horizontal', 'vertical', 'both', 'none'; "
        f"got {value!r}"
    )


def _normalize_source(source: str) -> str:
    if source == "auto":
        source = os.environ.get(SOURCE_ENV_VAR, source)
    if source in ("auto", "local", "cdn"):
        return source
    raise ValueError(f"source must be 'auto', 'local', or 'cdn'; got {source!r}")


def _iframe_mode() -> str:
    mode = os.environ.get(IFRAME_MODE_ENV_VAR, "auto")
    if mode in ("auto", "marimo", "srcdoc"):
        return mode
    raise ValueError(f"{IFRAME_MODE_ENV_VAR} must be 'auto', 'marimo', or 'srcdoc'; got {mode!r}")


def _module_urls(source: str) -> list[str]:
    source = _normalize_source(source)
    if source == "cdn":
        return [DEFAULT_CDN_URL]
    if source == "local":
        return [asset_urls()["js"]]

    try:
        return [asset_urls()["js"], DEFAULT_CDN_URL]
    except OSError:
        return [DEFAULT_CDN_URL]


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


def _render_script(replacements: dict[str, str]) -> str:
    script = _RENDER_TEMPLATE
    for key, value in replacements.items():
        script = script.replace(f"__EASYDOT_{key}__", value)
    if "__EASYDOT_" in script:
        raise RuntimeError("render.js contains an unreplaced easydot template placeholder")
    return script


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
    fit_toolbar_query = "null"
    if toolbar:
        fit_toolbar_query = "target.querySelector(':scope > [data-easydot-toolbar]')"
        toolbar_markup = (
            f"<style>{_toolbar_stylesheet(attr_id)}</style>"
            '<div class="easydot-toolbar" data-easydot-toolbar>'
            f'<button type="button" data-easydot-copy aria-label="Copy SVG to clipboard" title="Copy SVG">{COPY_ICON}</button>'
            f'<button type="button" data-easydot-download aria-label="Download SVG" title="Download SVG">{DOWNLOAD_ICON}</button>'
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
      const checkIcon = {_js_literal(CHECK_ICON)};
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

    script = _render_script(
        {
            "CONTAINER_ID": js_id,
            "MODULE_URLS": module_urls,
            "DOT_B64": dot_b64,
            "FORMAT_B64": safe_format,
            "ENGINE_B64": safe_engine,
            "SVG_INSTALL_JS": svg_install_js,
            "FIT": js_fit,
            "SCALE": js_scale,
            "SKIP_FRAME_RESIZE": js_skip_frame_resize,
            "FIT_TOOLBAR_QUERY": fit_toolbar_query,
            "TOOLBAR_SETUP_JS": toolbar_setup_js,
        }
    )

    return f"""
<style>{body_style}</style>
<div id="{attr_id}" style="{container_style}">{toolbar_markup}</div>
<script type="module">
{script}
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
        self.iframe_height = iframe_height
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
        height_attr = "" if self.iframe_height is None else f" height='{html_lib.escape(self.iframe_height, quote=True)}'"
        return f"<iframe srcdoc='{escaped}' width='100%'{height_attr} frameborder='0'></iframe>"

    def _mime_(self) -> tuple[str, str]:
        if not self.iframe:
            return "text/html", self._body_html()

        mode = _iframe_mode()
        if mode == "srcdoc":
            return "text/html", self._iframe_html()

        try:
            from marimo._output.formatting import iframe
        except ImportError:
            iframe = None

        if iframe is not None:
            kwargs = {} if self.iframe_height is None else {"height": self.iframe_height}
            frame = iframe(self._body_html(), **kwargs)
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
