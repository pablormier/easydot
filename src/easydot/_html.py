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


def _module_urls(source: str) -> list[str]:
    if source == "cdn":
        return [DEFAULT_CDN_URL]
    if source == "local":
        return [asset_urls()["js"]]
    if source != "auto":
        raise ValueError("source must be 'auto', 'local', or 'cdn'")

    try:
        return [asset_urls()["js"], DEFAULT_CDN_URL]
    except Exception:
        return [DEFAULT_CDN_URL]


def html(
    dot: str,
    *,
    engine: str = "dot",
    format: str = "svg",
    container_id: str | None = None,
    source: str = "auto",
) -> str:
    """Return browser HTML that renders DOT with the bundled Graphviz WASM module."""

    if container_id is None:
        container_id = f"easydot-{uuid.uuid4().hex}"

    dot_b64 = _b64_text(dot)
    module_urls = json.dumps(_module_urls(source))
    safe_engine = _b64_text(engine)
    safe_format = _b64_text(format)
    safe_id = html_lib.escape(container_id, quote=True)

    return f"""
<div id="{safe_id}" style="overflow:auto"></div>
<script type="module">
(async () => {{
  const target = document.getElementById("{safe_id}");
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
      const svg = target.querySelector("svg");
      const height = svg ? Math.ceil(svg.getBoundingClientRect().height) + 24 : target.scrollHeight + 24;
      if (window.frameElement) {{
        window.frameElement.style.height = `${{Math.max(120, height)}}px`;
      }}
    }} catch (_err) {{
      /* best effort only */
    }}
  }};
  try {{
    const moduleUrls = {module_urls};
    let mod = null;
    let lastError = null;
    for (const url of moduleUrls) {{
      try {{
        mod = await import(url);
        break;
      }} catch (error) {{
        lastError = error;
      }}
    }}
    if (!mod) {{
      throw lastError || new Error("Unable to load Graphviz WASM module");
    }}
    const Graphviz = mod.Graphviz || (mod.default && mod.default.Graphviz) || mod.default;
    if (!Graphviz || !Graphviz.load) {{
      throw new Error("Graphviz WASM module does not expose Graphviz.load()");
    }}
    const graphviz = await Graphviz.load();
    const svg = await graphviz.layout(decode("{dot_b64}"), decode("{safe_format}"), decode("{safe_engine}"));
    target.innerHTML = svg;
    resizeFrameToContent();
    requestAnimationFrame(resizeFrameToContent);
    setTimeout(resizeFrameToContent, 50);
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
        iframe_height: str = "220px",
        source: str = "auto",
    ) -> None:
        self.dot = dot
        self.engine = engine
        self.format = format
        self.iframe_height = iframe_height
        self.source = source

    def _body_html(self) -> str:
        return html(self.dot, engine=self.engine, format=self.format, source=self.source)

    def _iframe_html(self) -> str:
        escaped = html_lib.escape(self._body_html(), quote=True)
        return f"<iframe srcdoc='{escaped}' width='100%' height='{self.iframe_height}' frameborder='0'></iframe>"

    def _mime_(self) -> tuple[str, str]:
        try:
            from marimo._output.formatting import iframe

            frame = iframe(self._body_html(), height=self.iframe_height)
            frame_mime = getattr(frame, "_mime_", None)
            if callable(frame_mime):
                mime_type, payload = frame_mime()
                if mime_type == "text/html" and isinstance(payload, str):
                    return mime_type, payload
            payload = getattr(frame, "html", None)
            if isinstance(payload, str):
                return "text/html", payload
        except Exception:
            pass

        if "IPython" in sys.modules:
            return "text/html", self._iframe_html()
        return "text/html", self._body_html()

    def _repr_html_(self) -> str:
        if "IPython" in sys.modules:
            return self._iframe_html()
        return self._body_html()

    def __repr__(self) -> str:
        return self.dot


def display(
    dot: str,
    *,
    engine: str = "dot",
    format: str = "svg",
    iframe_height: str = "220px",
    source: str = "auto",
) -> DotDisplay:
    """Return a rich display object for a DOT graph."""

    return DotDisplay(dot, engine=engine, format=format, iframe_height=iframe_height, source=source)
