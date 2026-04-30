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
from easydot._display import (
    body_stylesheet,
    fit_lifecycle_script,
    layout_stylesheet,
    normalize_fit,
    toolbar_stylesheet,
)


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


# Keep _normalize_fit and _FIT_MODES for internal backward compat
_normalize_fit = normalize_fit
_FIT_MODES = ("none", "horizontal", "vertical", "both")


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


def _in_marimo_runtime() -> bool:
    try:
        from marimo._runtime import context
    except ImportError:
        return False
    runtime_context_installed = getattr(context, "runtime_context_installed", None)
    return bool(callable(runtime_context_installed) and runtime_context_installed())


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
    :class:`Graph` you can pass ``iframe_height`` to pin that height;
    otherwise it is inherited from whatever the host gives the iframe.

    ``format`` must be ``"svg"`` for fit/scale to apply correctly.
    """
    if format != "svg":
        raise ValueError(
            f"html() only supports format='svg' for fit/scale; got {format!r}. "
            "Use easydot.native() for non-SVG formats."
        )

    if container_id is None:
        container_id = f"easydot-{uuid.uuid4().hex}"

    dot = _dot_text(dot)
    fit_mode = normalize_fit(fit)
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

    body_style = body_stylesheet(fit_mode)
    layout_style = layout_stylesheet(attr_id)

    toolbar_markup = ""
    svg_install_js = "target.innerHTML = svg;"
    toolbar_setup_js = ""
    if toolbar:
        layout_style += toolbar_stylesheet(attr_id)
        toolbar_markup = (
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
            "FIT_LIFECYCLE_JS": fit_lifecycle_script(),
        }
    )

    return f"""
<style>{body_style}{layout_style}</style>
<div id="{attr_id}" class="easydot-fit-{fit_mode}">{toolbar_markup}</div>
<script type="module">
{script}
</script>
"""
