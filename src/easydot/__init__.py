"""Small helpers for browser-side Graphviz DOT rendering."""

from __future__ import annotations

import html as html_lib
import sys
import warnings
from importlib.metadata import version as _distribution_version

from easydot._capabilities import (
    BackendCapability,
    available_backends,
    capabilities,
    clear_capability_cache,
)
from easydot._version import UPSTREAM_PACKAGE, UPSTREAM_VERSION
from easydot._html import (
    DotSource,
    _dot_text,
    _b64_text,
    _normalize_iframe_mode,
    _iframe_mode,
    _in_pycharm,
    _in_marimo_runtime,
    html as _browser_html,
)
import easydot._native as _native_module
import easydot._wasm as _wasm_module
from easydot._native import native, native_svg
from easydot._server import asset_base_url, asset_urls, shutdown_server
from easydot._wasm import svg as _wasm_svg
from easydot._display import normalize_fit, wrap_static_html

__version__ = _distribution_version("easydot")

_STATIC_BACKENDS = ("wasm", "native")
_BROWSER_ONLY_KWARGS = ("worker", "spinner", "source", "iframe_mode")

_DEFAULT_VIEWPORT_FIT_HEIGHT = "400px"


def _backend_error() -> str:
    return "backend must be 'auto', 'browser', 'wasm', or 'native'"


def _select_auto_backend(kwargs: dict[str, object]) -> str:
    timeout = kwargs.pop("capability_timeout", 2.0)
    check_cdn = kwargs.pop("check_cdn", True)
    refresh = kwargs.pop("refresh_capabilities", False)
    engine = kwargs.get("engine", "dot")
    if not isinstance(engine, str):
        raise TypeError("engine must be a string")
    if not isinstance(timeout, int | float):
        raise TypeError("capability_timeout must be a number")

    probed = capabilities(
        engine=engine,
        timeout=float(timeout),
        check_cdn=bool(check_cdn),
        refresh=bool(refresh),
    )

    if probed["native"].available:
        return "native"
    if probed["wasm"].available:
        return "wasm"

    browser = probed["browser"]
    details = browser.details
    source = kwargs.get("source", "auto")
    if source == "local":
        if details.get("local") is True:
            return "browser"
    elif source == "cdn":
        if details.get("cdn") is True:
            return "browser"
    elif source == "auto":
        if details.get("local") is True:
            kwargs["source"] = "local"
            return "browser"
        if details.get("cdn") is True:
            kwargs["source"] = "cdn"
            return "browser"
    else:
        raise ValueError(f"source must be 'auto', 'local', or 'cdn'; got {source!r}")

    reasons = {
        name: capability.reason or "unavailable"
        for name, capability in probed.items()
        if not capability.available
    }
    if browser.available:
        reasons["browser"] = f"source {source!r} is unavailable"
    raise RuntimeError(f"no easydot backend is available: {reasons}")


def _select_svg_auto_backend(kwargs: dict[str, object]) -> str:
    """Auto-select backend for svg() — browser is never chosen."""
    timeout = kwargs.pop("capability_timeout", 2.0)
    check_cdn = kwargs.pop("check_cdn", True)
    refresh = kwargs.pop("refresh_capabilities", False)
    engine = kwargs.get("engine", "dot")
    if not isinstance(engine, str):
        raise TypeError("engine must be a string")
    if not isinstance(timeout, int | float):
        raise TypeError("capability_timeout must be a number")

    probed = capabilities(
        engine=engine,
        timeout=float(timeout),
        check_cdn=bool(check_cdn),
        refresh=bool(refresh),
    )

    if probed["native"].available:
        return "native"
    if probed["wasm"].available:
        return "wasm"

    reasons = {
        name: probed[name].reason or "unavailable"
        for name in ("native", "wasm")
        if not probed[name].available
    }
    raise RuntimeError(
        f"no SVG-producing backend is available (browser cannot produce SVG synchronously): {reasons}"
    )


def svg(dot: str | DotSource, *, backend: str = "auto", engine: str = "dot", **kwargs) -> str:
    """Render a DOT graph to a raw SVG string.

    Only the ``wasm`` and ``native`` backends can produce SVG synchronously.
    ``backend='browser'`` raises because the browser backend renders in the
    browser at view-time. Use ``backend='auto'`` (default) to select the first
    available SVG-producing backend (native preferred over wasm).

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    backend:
        ``"auto"`` (default), ``"wasm"``, or ``"native"``. ``"browser"`` raises.
    engine:
        Graphviz layout engine (e.g. ``dot``, ``neato``, ``circo``).

    Returns
    -------
    str
        Raw SVG string.
    """
    if backend == "browser":
        raise ValueError(
            "backend='browser' renders in the browser at view-time and cannot produce "
            "a synchronous SVG string. Use backend='wasm', backend='native', or "
            "backend='auto' for a synchronous SVG string."
        )
    if backend == "auto":
        backend = _select_svg_auto_backend(kwargs)
    if backend == "wasm":
        return _wasm_module.svg(dot, engine=engine)
    if backend == "native":
        result = _native_module.native(dot, engine=engine, format="svg")
        assert isinstance(result, str)
        return result
    raise ValueError(f"{_backend_error()}; got {backend!r}")


def html(
    dot: str | DotSource,
    *,
    backend: str = "auto",
    engine: str = "dot",
    fit: bool | str = False,
    scale: float = 1.0,
    toolbar: bool = True,
    # Browser-only options
    source: str = "auto",
    spinner: bool = True,
    worker: bool | str = False,
    container_id: str | None = None,
    # Auto-backend options
    capability_timeout: float = 2.0,
    check_cdn: bool = True,
    refresh_capabilities: bool = False,
) -> str:
    """Return display-ready HTML for a DOT graph.

    Works for all backends. ``fit`` and ``scale`` apply to all three:

    - ``fit=False`` (default): natural size × scale.
    - ``fit="horizontal"``: width fits the container, height follows aspect ratio.
    - ``fit="vertical"``: height fits the container, width follows aspect ratio.
    - ``fit=True`` / ``fit="both"``: both axes fit the container.

    ``source``, ``spinner``, and ``worker`` are browser-only options and raise
    ``TypeError`` when used with ``backend="wasm"`` or ``backend="native"``.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    backend:
        ``"auto"``, ``"browser"``, ``"wasm"``, or ``"native"``.
    engine:
        Graphviz layout engine.
    fit:
        Fit mode — ``False``, ``True``, ``"none"``, ``"horizontal"``,
        ``"vertical"``, or ``"both"``.
    scale:
        Scale factor applied to the SVG natural size.
    toolbar:
        Whether to include copy/download toolbar buttons.
    source:
        Browser-only. Asset source: ``"auto"``, ``"local"``, or ``"cdn"``.
    spinner:
        Browser-only. Show a loading spinner while rendering.
    worker:
        Browser-only. Web Worker mode: ``False``, ``True``, or ``"auto"``.
    """
    if backend == "auto":
        _kwargs = dict(
            engine=engine,
            source=source,
            capability_timeout=capability_timeout,
            check_cdn=check_cdn,
            refresh_capabilities=refresh_capabilities,
        )
        backend = _select_auto_backend(_kwargs)
        source = _kwargs.pop("source", source)

    fit_mode = normalize_fit(fit)

    if backend == "browser":
        return _browser_html(
            dot,
            engine=engine,
            container_id=container_id,
            source=source,
            fit=fit_mode,
            scale=scale,
            spinner=spinner,
            toolbar=toolbar,
            worker=worker,
        )

    if backend in _STATIC_BACKENDS:
        _reject_browser_only_kwargs(backend, source=source, spinner=spinner, worker=worker)
        raw_svg = _get_static_svg(dot, backend=backend, engine=engine)
        return wrap_static_html(
            raw_svg,
            fit=fit_mode,
            scale=scale,
            toolbar=toolbar,
            container_id=container_id,
        )

    raise ValueError(f"{_backend_error()}; got {backend!r}")


def _reject_browser_only_kwargs(
    backend: str,
    *,
    source: str,
    spinner: bool,
    worker: bool | str,
) -> None:
    if source != "auto":
        raise TypeError(f"source is only supported by backend='browser'; got backend={backend!r}")
    if worker is not False:
        raise TypeError(f"worker is only supported by backend='browser'; got backend={backend!r}")
    if not spinner:
        raise TypeError(f"spinner is only supported by backend='browser'; got backend={backend!r}")


def _get_static_svg(dot: str | DotSource, *, backend: str, engine: str) -> str:
    if backend == "wasm":
        return _wasm_module.svg(dot, engine=engine)
    if backend == "native":
        result = _native_module.native(dot, engine=engine, format="svg")
        assert isinstance(result, str)
        return result
    raise ValueError(f"{_backend_error()}; got {backend!r}")


class Graph:
    """Rich display object for a DOT graph.

    Supports all three backends (browser, wasm, native) and all fit modes.
    Use :func:`render` to construct instances.
    """

    def __init__(
        self,
        dot: str | DotSource,
        *,
        backend: str = "auto",
        engine: str = "dot",
        fit: bool | str = False,
        scale: float = 1.0,
        toolbar: bool = True,
        iframe: bool = True,
        iframe_height: str | None = None,
        iframe_mode: str | None = None,
        spinner: bool = True,
        worker: bool | str = False,
        source: str = "auto",
    ) -> None:
        self.dot = _dot_text(dot)
        self.backend = backend
        self.engine = engine
        self.fit = fit
        self.scale = scale
        self.toolbar = toolbar
        self.iframe = iframe
        self.iframe_height = iframe_height
        self.iframe_mode = (
            _normalize_iframe_mode(iframe_mode) if iframe_mode is not None else None
        )
        self.spinner = spinner
        self.worker = worker
        self.source = source
        self._resolved_backend: str | None = None
        self._svg_cache: str | None = None

    def _resolve_backend(self) -> str:
        if self._resolved_backend is not None:
            return self._resolved_backend
        if self.backend != "auto":
            self._resolved_backend = self.backend
            return self._resolved_backend
        kwargs: dict[str, object] = dict(engine=self.engine, source=self.source)
        self._resolved_backend = _select_auto_backend(kwargs)
        # _select_auto_backend may set source="local"/"cdn" for browser
        if "source" in kwargs:
            self.source = str(kwargs["source"])
        return self._resolved_backend

    def _body_html(self) -> str:
        return html(
            self.dot,
            backend=self._resolve_backend(),
            engine=self.engine,
            fit=self.fit,
            scale=self.scale,
            toolbar=self.toolbar,
            source=self.source,
            spinner=self.spinner,
            worker=self.worker,
        )

    def _raw_svg(self) -> str | None:
        backend = self._resolve_backend()
        if backend == "browser":
            return None
        if self._svg_cache is None:
            self._svg_cache = _get_static_svg(self.dot, backend=backend, engine=self.engine)
        return self._svg_cache

    # ---------- iframe plumbing (mirrors old DotDisplay logic) ----------

    def _iframe_html(self, *, mode: str = "srcdoc") -> str:
        body_html = self._body_html()
        escaped = html_lib.escape(body_html, quote=True)

        backend = self._resolve_backend()
        fit_mode = normalize_fit(self.fit)
        height = self.iframe_height
        if height is None and backend in _STATIC_BACKENDS and fit_mode in ("vertical", "both"):
            height = _DEFAULT_VIEWPORT_FIT_HEIGHT

        height_attr = (
            ""
            if height is None
            else f" height='{html_lib.escape(height, quote=True)}'"
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

        height = self.iframe_height
        if height is None and self._resolve_backend() in _STATIC_BACKENDS:
            fit_mode = normalize_fit(self.fit)
            if fit_mode in ("vertical", "both"):
                height = _DEFAULT_VIEWPORT_FIT_HEIGHT

        kwargs = {} if height is None else {"height": height}
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

        if mode == "managed" or (mode == "auto" and _in_marimo_runtime()):
            payload = self._managed_iframe_html()
            if payload is not None:
                return payload

        return self._iframe_html(mode="srcdoc")

    # ---------- rich display protocol ----------

    def _mime_(self) -> tuple[str, str]:
        return "text/html", self._html_payload()

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, str]:
        mime_type, payload = self._mime_()
        bundle: dict[str, str] = {mime_type: payload}
        raw_svg = self._raw_svg()
        if raw_svg is not None:
            bundle["image/svg+xml"] = raw_svg
        return bundle

    def _ipython_display_(self) -> None:
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

    def _repr_svg_(self) -> str | None:
        return self._raw_svg()

    def __repr__(self) -> str:
        return self.dot


def render(
    dot: str | DotSource,
    *,
    backend: str = "auto",
    capability_timeout: float = 2.0,
    check_cdn: bool = True,
    refresh_capabilities: bool = False,
    **kwargs,
) -> "Graph":
    """Return a rich display object for a DOT graph.

    Parameters
    ----------
    dot:
        A DOT source string or an object with a ``to_string()`` method.
    backend:
        ``"auto"`` to choose the first available backend (native → wasm →
        browser), ``"browser"`` for interactive browser-side rendering,
        ``"wasm"`` for static SVG via wasi-graphviz, or ``"native"`` for static
        SVG via installed Graphviz executables.
    capability_timeout:
        Timeout in seconds for backend capability probes (auto backend only).
    check_cdn:
        Whether to probe the CDN URL when checking browser availability.
    refresh_capabilities:
        Force re-probing even if cached results exist.
    **kwargs:
        Forwarded to :class:`Graph` (``engine``, ``fit``, ``scale``,
        ``toolbar``, ``iframe``, ``iframe_height``, ``iframe_mode``,
        ``spinner``, ``worker``, ``source``).

    Returns
    -------
    Graph
    """
    if backend == "auto":
        _kwargs = dict(
            capability_timeout=capability_timeout,
            check_cdn=check_cdn,
            refresh_capabilities=refresh_capabilities,
            **kwargs,
        )
        backend = _select_auto_backend(_kwargs)
        kwargs = _kwargs
    elif backend not in ("browser", "wasm", "native"):
        raise ValueError(f"{_backend_error()}; got {backend!r}")
    return Graph(dot, backend=backend, **kwargs)


def to_string(dot: str | DotSource, *, backend: str = "auto", **kwargs) -> str:
    """Render a DOT graph to a string.

    .. deprecated::
        Use :func:`html` for HTML output or :func:`svg` for SVG output instead.
        ``to_string()`` returns different types depending on the backend
        (HTML for browser, SVG for wasm/native), which is confusing.
    """
    warnings.warn(
        "to_string() is deprecated; use html() for HTML output or svg() for SVG output.",
        DeprecationWarning,
        stacklevel=2,
    )
    if backend == "auto":
        _kwargs = dict(**kwargs)
        backend = _select_auto_backend(_kwargs)
        kwargs = _kwargs
    import easydot._html as _html_module
    if backend == "browser":
        return _html_module.html(dot, **kwargs)
    if backend == "wasm":
        return _wasm_module.svg(dot, engine=kwargs.get("engine", "dot"))
    if backend == "native":
        result = _native_module.native_svg(dot, engine=kwargs.get("engine", "dot"))
        return result
    raise ValueError(f"{_backend_error()}; got {backend!r}")


# ---------- deprecated aliases ----------

def _deprecated(name: str, replacement: str) -> None:
    warnings.warn(
        f"easydot.{name} is deprecated; use {replacement} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


class DotDisplay(Graph):
    """Deprecated. Use :class:`Graph` or :func:`render` instead."""

    def __init__(self, dot: str | DotSource, **kwargs) -> None:
        super().__init__(dot, backend="browser", **kwargs)


class SvgDisplay(Graph):
    """Deprecated. Use :class:`Graph` or :func:`render` instead."""

    def __init__(self, dot: str | DotSource, *, engine: str = "dot") -> None:
        super().__init__(dot, backend="wasm", engine=engine)


class NativeSvgDisplay(Graph):
    """Deprecated. Use :class:`Graph` or :func:`render` instead."""

    def __init__(self, dot: str | DotSource, *, engine: str = "dot") -> None:
        super().__init__(dot, backend="native", engine=engine)


def display(
    dot: str | DotSource,
    *,
    engine: str = "dot",
    fit: bool | str = False,
    scale: float = 1.0,
    toolbar: bool = True,
    iframe: bool = True,
    iframe_height: str | None = None,
    iframe_mode: str | None = None,
    spinner: bool = True,
    worker: bool | str = False,
    source: str = "auto",
) -> Graph:
    """Deprecated. Use :func:`render` instead."""
    _deprecated("display", "easydot.render")
    return Graph(
        dot,
        backend="browser",
        engine=engine,
        fit=fit,
        scale=scale,
        toolbar=toolbar,
        iframe=iframe,
        iframe_height=iframe_height,
        iframe_mode=iframe_mode,
        spinner=spinner,
        worker=worker,
        source=source,
    )


def display_svg(dot: str | DotSource, *, engine: str = "dot") -> "SvgDisplay":
    """Deprecated. Use :func:`render` with ``backend='wasm'`` instead."""
    warnings.warn(
        "easydot.display_svg is deprecated; use easydot.render(..., backend='wasm') instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return SvgDisplay(dot, engine=engine)


def display_native_svg(dot: str | DotSource, *, engine: str = "dot") -> "NativeSvgDisplay":
    """Deprecated. Use :func:`render` with ``backend='native'`` instead."""
    warnings.warn(
        "easydot.display_native_svg is deprecated; use easydot.render(..., backend='native') instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return NativeSvgDisplay(dot, engine=engine)


__all__ = [
    "Graph",
    "BackendCapability",
    "UPSTREAM_PACKAGE",
    "UPSTREAM_VERSION",
    "__version__",
    "asset_base_url",
    "asset_urls",
    "available_backends",
    "capabilities",
    "clear_capability_cache",
    "html",
    "native",
    "native_svg",
    "render",
    "shutdown_server",
    "svg",
    "to_string",
    # deprecated
    "DotDisplay",
    "NativeSvgDisplay",
    "SvgDisplay",
    "display",
    "display_native_svg",
    "display_svg",
]
