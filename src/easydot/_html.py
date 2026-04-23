"""HTML helpers for browser-side DOT rendering."""

from __future__ import annotations

import base64
import html as html_lib
import json
import os
import sys
import uuid
from importlib.resources import files
from typing import Protocol

from easydot._icons import CHECK_ICON, COPY_ICON, DOWNLOAD_ICON, STOP_ICON
from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._server import asset_urls


class DotSource(Protocol):
    def to_string(self) -> str: ...


DEFAULT_CDN_URL = f"https://cdn.jsdelivr.net/npm/{UPSTREAM_PACKAGE}@{UPSTREAM_VERSION}/dist/index.min.js"
SOURCE_ENV_VAR = "EASYDOT_SOURCE"
IFRAME_MODE_ENV_VAR = "EASYDOT_IFRAME_MODE"
_ASSET_PACKAGE = "easydot.assets"
_RENDER_TEMPLATE = files(_ASSET_PACKAGE).joinpath("render.js").read_text(encoding="utf-8")


def _b64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _dot_text(dot: str | DotSource) -> str:
    if isinstance(dot, str):
        return dot
    to_string = getattr(dot, "to_string", None)
    if not callable(to_string):
        raise TypeError("dot must be a DOT string or an object with a to_string() method")
    value = to_string()
    if not isinstance(value, str):
        raise TypeError("dot.to_string() must return a string")
    return value


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


def _normalize_worker(value: bool | str) -> str:
    if value is True:
        return "require"
    if value is False:
        return "disabled"
    if value == "auto":
        return "auto"
    raise ValueError("worker must be 'auto', True, or False")


def _normalize_source(source: str) -> str:
    if source == "auto":
        source = os.environ.get(SOURCE_ENV_VAR, source)
    if source in ("auto", "local", "cdn"):
        return source
    raise ValueError(f"source must be 'auto', 'local', or 'cdn'; got {source!r}")


def _normalize_iframe_mode(mode: str | None) -> str:
    if mode is None:
        mode = os.environ.get(IFRAME_MODE_ENV_VAR, "auto")
    if mode in ("auto", "managed", "srcdoc", "data"):
        return mode
    raise ValueError(
        "iframe_mode must be 'auto', 'managed', 'srcdoc', or 'data'; "
        f"got {mode!r}"
    )


def _iframe_mode() -> str:
    try:
        return _normalize_iframe_mode(os.environ.get(IFRAME_MODE_ENV_VAR, "auto"))
    except ValueError as error:
        message = str(error).replace("iframe_mode", IFRAME_MODE_ENV_VAR, 1)
        raise ValueError(message) from None


def _in_pycharm() -> bool:
    return os.environ.get("PYCHARM_HOSTED") == "1"


def _module_urls(source: str) -> list[str]:
    source = _normalize_source(source)
    if source == "cdn":
        return [DEFAULT_CDN_URL]
    if source == "local":
        return [asset_urls()["js"]]

    try:
        return [DEFAULT_CDN_URL, asset_urls()["js"]]
    except OSError:
        return [DEFAULT_CDN_URL]


def _layout_stylesheet(attr_id: str) -> str:
    """CSS that implements the two-axis fit model.

    Width axis: natural*scale (default) or fit-container (horizontal, both).
    Height axis: natural*scale (default) or fit-viewport (vertical, both).
    The browser does all the math via calc() + flexbox; JS only sets the
    --easydot-nat-w/--easydot-nat-h/--easydot-scale custom properties.
    """

    return (
        f"#{attr_id}{{box-sizing:border-box;--easydot-scale:1}}"
        f"#{attr_id} > svg{{display:block}}"
        f"#{attr_id} .easydot-status{{"
        "display:inline-flex;align-items:center;gap:8px;padding:8px;"
        "color:#555;font:13px system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "box-sizing:border-box"
        "}"
        f"#{attr_id} .easydot-status.is-warning{{color:#8a5a00}}"
        f"#{attr_id} .easydot-spinner{{"
        "width:14px;height:14px;border:2px solid #d0d0d0;border-top-color:currentColor;"
        "border-radius:50%;animation:easydot-spin 800ms linear infinite;box-sizing:border-box"
        "}"
        f"#{attr_id} .easydot-stop{{"
        "background:transparent;border:0;border-radius:4px;padding:2px;"
        "margin:0;cursor:pointer;color:#6b6b6b;line-height:0;"
        "transition:color 120ms ease-in-out,background-color 120ms ease-in-out;"
        "}"
        f"#{attr_id} .easydot-stop:hover{{color:#b00020;background:rgba(176,0,32,0.08)}}"
        "@keyframes easydot-spin{to{transform:rotate(360deg)}}"
        f"#{attr_id}.easydot-fit-none{{overflow:auto}}"
        f"#{attr_id}.easydot-fit-none.easydot-scaled > svg{{"
        "width:calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px);"
        "height:calc(var(--easydot-nat-h) * var(--easydot-scale) * 1px);"
        "}"
        f"#{attr_id}.easydot-fit-horizontal > svg{{"
        "width:100%;height:auto;"
        "max-width:calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px);"
        "}"
        f"#{attr_id}.easydot-fit-vertical,"
        f"#{attr_id}.easydot-fit-both{{"
        "display:flex;flex-direction:column;align-items:center;"
        "height:100%;min-height:0"
        "}"
        f"#{attr_id}.easydot-fit-vertical > .easydot-toolbar,"
        f"#{attr_id}.easydot-fit-both > .easydot-toolbar{{"
        "flex:0 0 auto;align-self:stretch"
        "}"
        f"#{attr_id}.easydot-fit-vertical{{overflow-x:auto;overflow-y:hidden}}"
        f"#{attr_id}.easydot-fit-vertical > svg{{"
        "flex:1 1 0;min-height:0;"
        "max-height:calc(var(--easydot-nat-h) * var(--easydot-scale) * 1px);"
        "aspect-ratio:var(--easydot-nat-w) / var(--easydot-nat-h);"
        "height:100%;width:auto"
        "}"
        f"#{attr_id}.easydot-fit-both{{overflow:hidden}}"
        f"#{attr_id}.easydot-fit-both > svg{{"
        "flex:0 1 auto;min-width:0;min-height:0;"
        "max-width:min(100%,calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px));"
        "max-height:min(100%,calc(var(--easydot-nat-h) * var(--easydot-scale) * 1px));"
        "aspect-ratio:var(--easydot-nat-w) / var(--easydot-nat-h);"
        "width:auto;height:auto"
        "}"
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


def _render_script(replacements: dict[str, str]) -> str:
    script = _RENDER_TEMPLATE
    for key, value in replacements.items():
        script = script.replace(f"__EASYDOT_{key}__", value)
    if "__EASYDOT_" in script:
        raise RuntimeError("render.js contains an unreplaced easydot template placeholder")
    return script


def html(
    dot: str | DotSource,
    *,
    engine: str = "dot",
    format: str = "svg",
    container_id: str | None = None,
    source: str = "auto",
    fit: bool | str = False,
    scale: float = 1.0,
    spinner: bool = True,
    toolbar: bool = True,
    worker: bool | str = False,
) -> str:
    """Return browser HTML that renders DOT with the bundled Graphviz WASM module.

    Fit modes choose how the rendered SVG is sized on two independent axes:

    - ``fit=False`` (default): both width and height are the SVG's natural size
      times ``scale``. The iframe grows to fit the content.
    - ``fit="horizontal"``: width fits the container (capped at natural*scale),
      height follows the SVG's aspect ratio. The iframe grows to content.
    - ``fit="vertical"``: height fits the iframe viewport (capped at
      natural*scale), width follows aspect ratio. Horizontal scroll if needed.
    - ``fit=True`` / ``fit="both"``: both axes fit the iframe viewport, aspect
      preserved.

    Viewport-fit modes (``"vertical"``, ``"both"``) rely on ``100%`` of the
    iframe height set by the host (marimo/Jupyter/srcdoc). If you embed via
    :class:`DotDisplay` you can pass ``iframe_height`` to pin that height;
    otherwise it is inherited from whatever the host gives the iframe.
    """

    if container_id is None:
        container_id = f"easydot-{uuid.uuid4().hex}"

    dot = _dot_text(dot)
    fit_mode = _normalize_fit(fit)
    worker_mode = _normalize_worker(worker)
    dot_b64 = _b64_text(dot)
    module_urls = _js_literal(_module_urls(source))
    safe_engine = _b64_text(engine)
    safe_format = _b64_text(format)
    attr_id = html_lib.escape(container_id, quote=True)
    js_id = _js_literal(container_id)
    js_fit = _js_literal(fit_mode)
    js_scale = _js_literal(float(scale))
    js_format = _js_literal(format)
    js_show_spinner = _js_literal(bool(spinner))
    js_worker_mode = _js_literal(worker_mode)

    if fit_mode in ("vertical", "both"):
        body_style = "html,body{margin:0;padding:0;height:100%;overflow:hidden}"
    else:
        body_style = "html,body{margin:0;padding:0}"
    layout_style = _layout_stylesheet(attr_id)

    toolbar_markup = ""
    svg_install_js = "target.innerHTML = svg;"
    toolbar_setup_js = ""
    if toolbar:
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
            "SHOW_SPINNER": js_show_spinner,
            "WORKER_MODE": js_worker_mode,
            "TOOLBAR_SETUP_JS": toolbar_setup_js,
            "STOP_ICON": _js_literal(STOP_ICON),
        }
    )

    return f"""
<style>{body_style}{layout_style}</style>
<div id="{attr_id}" class="easydot-fit-{fit_mode}">{toolbar_markup}</div>
<script type="module">
{script}
</script>
"""


class DotDisplay:
    """Rich display wrapper for DOT graphs."""

    def __init__(
        self,
        dot: str | DotSource,
        *,
        engine: str = "dot",
        format: str = "svg",
        iframe_height: str | None = None,
        source: str = "auto",
        fit: bool | str = False,
        scale: float = 1.0,
        iframe: bool = True,
        iframe_mode: str | None = None,
        spinner: bool = True,
        toolbar: bool = True,
        worker: bool | str = False,
    ) -> None:
        self.dot = _dot_text(dot)
        self.engine = engine
        self.format = format
        self.iframe_height = iframe_height
        self.source = source
        self.fit = fit
        self.scale = scale
        self.iframe = iframe
        self.iframe_mode = (
            _normalize_iframe_mode(iframe_mode)
            if iframe_mode is not None
            else None
        )
        self.spinner = spinner
        self.toolbar = toolbar
        self.worker = worker

    def _body_html(self) -> str:
        return html(
            self.dot,
            engine=self.engine,
            format=self.format,
            source=self.source,
            fit=self.fit,
            scale=self.scale,
            spinner=self.spinner,
            toolbar=self.toolbar,
            worker=self.worker,
        )

    def _iframe_html(self, *, mode: str = "srcdoc") -> str:
        body_html = self._body_html()
        escaped = html_lib.escape(body_html, quote=True)
        height_attr = (
            ""
            if self.iframe_height is None
            else f" height='{html_lib.escape(self.iframe_height, quote=True)}'"
        )
        if mode == "data":
            src = f"data:text/html;charset=utf-8;base64,{_b64_text(body_html)}"
            escaped_src = html_lib.escape(src, quote=True)
            return (
                f"<iframe src='{escaped_src}' width='100%'{height_attr} "
                "frameborder='0'></iframe>"
            )
        return f"<iframe srcdoc='{escaped}' width='100%'{height_attr} frameborder='0'></iframe>"

    def _configured_iframe_mode(self) -> str:
        return _iframe_mode() if self.iframe_mode is None else self.iframe_mode

    def _managed_iframe_html(self) -> str | None:
        try:
            from marimo._output.formatting import iframe
        except ImportError:
            return None

        kwargs = {} if self.iframe_height is None else {"height": self.iframe_height}
        frame = iframe(self._body_html(), **kwargs)
        frame_mime = getattr(frame, "_mime_", None)
        if callable(frame_mime):
            mime_type, payload = frame_mime()
            if mime_type == "text/html" and isinstance(payload, str):
                return payload
        payload = getattr(frame, "html", None)
        if isinstance(payload, str):
            return payload
        return None

    def _html_payload(self) -> str:
        if not self.iframe:
            return self._body_html()

        mode = self._configured_iframe_mode()
        if mode == "data" or (mode == "auto" and _in_pycharm()):
            return self._iframe_html(mode="data")
        if mode == "srcdoc":
            return self._iframe_html(mode="srcdoc")

        if mode == "managed" or mode == "auto":
            payload = self._managed_iframe_html()
            if payload is not None:
                return payload

        return self._iframe_html(mode="srcdoc")

    def _mime_(self) -> tuple[str, str]:
        return "text/html", self._html_payload()

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
        return self._html_payload()

    def __repr__(self) -> str:
        return self.dot


def display(
    dot: str | DotSource,
    *,
    engine: str = "dot",
    format: str = "svg",
    iframe_height: str | None = None,
    source: str = "auto",
    fit: bool | str = False,
    scale: float = 1.0,
    iframe: bool = True,
    iframe_mode: str | None = None,
    spinner: bool = True,
    toolbar: bool = True,
    worker: bool | str = False,
) -> DotDisplay:
    """Return a rich display object for a DOT graph.

    See :func:`html` for the ``fit``/``scale`` contract. ``iframe_height`` sets
    the wrapping iframe's height attribute; viewport-fit modes (``"vertical"``,
    ``"both"``) use the iframe height the host provides unless you pass this
    kwarg to pin it explicitly. ``iframe_mode`` controls the outer notebook
    wrapper and defaults to ``EASYDOT_IFRAME_MODE``.
    """

    return DotDisplay(
        dot,
        engine=engine,
        format=format,
        iframe_height=iframe_height,
        source=source,
        fit=fit,
        scale=scale,
        iframe=iframe,
        iframe_mode=iframe_mode,
        spinner=spinner,
        toolbar=toolbar,
        worker=worker,
    )
