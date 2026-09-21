"""Runtime capability probes for easydot backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.request import Request, urlopen

from easydot._html import DEFAULT_CDN_URL
from easydot._native import native, native_svg
from easydot._server import asset_urls
from easydot._wasm import render as wasm_render, svg

_PROBE_DOT = "digraph { easydot_probe -> ok }"
_CACHE: dict[tuple[str, float, bool], dict[str, "BackendCapability"]] = {}
_STATIC_CACHE: dict[tuple[str, str], dict[str, "BackendCapability"]] = {}
_STATIC_SELECTION_CACHE: dict[
    tuple[str, str], tuple[str | None, dict[str, "BackendCapability"]]
] = {}


def _is_hosted_environment() -> bool:
    """Return True if running in a known hosted remote environment."""
    import os
    import sys

    if "google.colab" in sys.modules:
        return True
    if "KAGGLE_KERNEL_RUN_TYPE" in os.environ:
        return True
    if "SAGEMAKER_INTERNAL_IMAGE_URI" in os.environ:
        return True
    if "BINDER_PORT" in os.environ:
        return True
    if "JUPYTERHUB_API_TOKEN" in os.environ:
        return True
    if "CODESPACES" in os.environ or "GITPOD_WORKSPACE_ID" in os.environ:
        return True
    return False


@dataclass(frozen=True)
class BackendCapability:
    """Runtime availability for one easydot backend."""

    backend: str
    available: bool
    reason: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def _failure_reason(error: BaseException) -> str:
    message = str(error)
    if message:
        return f"{type(error).__name__}: {message}"
    return type(error).__name__


def _probe_url(url: str, *, timeout: float) -> tuple[bool, str | None]:
    try:
        request = Request(url, method="HEAD")
        with urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 400:
                return True, None
            return False, f"HTTP status {response.status}"
    except Exception as exc:
        return False, _failure_reason(exc)


def _browser_capability(*, timeout: float, check_cdn: bool) -> BackendCapability:
    local_url: str | None = None
    if _is_hosted_environment():
        local_available = False
        local_reason = "local server unreachable from client browser in hosted environment"
    else:
        try:
            local_url = asset_urls()["js"]
            local_available, local_reason = _probe_url(local_url, timeout=timeout)
        except Exception as exc:
            local_available = False
            local_reason = _failure_reason(exc)

    if check_cdn:
        cdn_available, cdn_reason = _probe_url(DEFAULT_CDN_URL, timeout=timeout)
    else:
        cdn_available = False
        cdn_reason = "not checked"

    details: dict[str, object] = {
        "local": local_available,
        "cdn": cdn_available,
        "local_url": local_url,
        "cdn_url": DEFAULT_CDN_URL,
    }
    if local_reason is not None:
        details["local_reason"] = local_reason
    if cdn_reason is not None:
        details["cdn_reason"] = cdn_reason

    if local_available or cdn_available:
        return BackendCapability("browser", True, details=details)

    return BackendCapability(
        "browser",
        False,
        "neither local browser assets nor CDN assets are reachable",
        details,
    )


def _wasm_capability(*, engine: str, format: str = "svg") -> BackendCapability:
    try:
        rendered = (
            svg(_PROBE_DOT, engine=engine)
            if format == "svg"
            else wasm_render(_PROBE_DOT, format=format, engine=engine)
        )
    except Exception as exc:
        return BackendCapability("wasm", False, _failure_reason(exc))
    valid = (
        (isinstance(rendered, str) and ("<svg" in rendered or "<?xml" in rendered))
        if format == "svg"
        else isinstance(rendered, bytes) and bool(rendered)
    )
    return BackendCapability(
        "wasm",
        valid,
        None
        if valid
        else ("probe did not return SVG" if format == "svg" else f"probe did not return {format}"),
        {"engine": engine} if format == "svg" else {"engine": engine, "format": format},
    )


def _native_capability(*, engine: str, format: str = "svg") -> BackendCapability:
    try:
        rendered = (
            native_svg(_PROBE_DOT, engine=engine)
            if format == "svg"
            else native(_PROBE_DOT, engine=engine, format=format)
        )
    except Exception as exc:
        return BackendCapability("native", False, _failure_reason(exc), {"engine": engine})
    valid = (
        (isinstance(rendered, str) and ("<svg" in rendered or "<?xml" in rendered))
        if format == "svg"
        else isinstance(rendered, bytes) and bool(rendered)
    )
    return BackendCapability(
        "native",
        valid,
        None
        if valid
        else ("probe did not return SVG" if format == "svg" else f"probe did not return {format}"),
        {"engine": engine} if format == "svg" else {"engine": engine, "format": format},
    )


def capabilities(
    *,
    engine: str = "dot",
    timeout: float = 2.0,
    check_cdn: bool = True,
    refresh: bool = False,
) -> dict[str, BackendCapability]:
    """Probe easydot backend availability in the current runtime.

    The probes execute a tiny graph for server-side backends instead of only
    checking imports or executable presence. This catches environments where a
    dependency is installed but unusable, such as restricted subprocess
    runtimes or WASI runtimes that cannot initialize.
    """
    key = (engine, float(timeout), bool(check_cdn))
    if not refresh and key in _CACHE:
        return _CACHE[key]

    result = {
        "browser": _browser_capability(timeout=timeout, check_cdn=check_cdn),
        "wasm": _wasm_capability(engine=engine),
        "native": _native_capability(engine=engine),
    }
    _CACHE[key] = result
    return result


def static_capabilities(
    *,
    engine: str = "dot",
    format: str = "svg",
    refresh: bool = False,
) -> dict[str, BackendCapability]:
    """Probe synchronous native and WASM backends for one output format.

    Unlike :func:`capabilities`, this does not inspect browser assets and its
    result is specific to the requested static format.
    """
    key = (engine, format)
    if not refresh and key in _STATIC_CACHE:
        return _STATIC_CACHE[key]

    result = {
        "native": _native_capability(engine=engine, format=format),
        "wasm": _wasm_capability(engine=engine, format=format),
    }
    _STATIC_CACHE[key] = result
    return result


def select_static_backend(
    *,
    engine: str = "dot",
    format: str = "svg",
    refresh: bool = False,
) -> tuple[str | None, dict[str, BackendCapability]]:
    """Select a synchronous backend, probing WASM only after native fails."""
    key = (engine, format)
    if not refresh and key in _STATIC_SELECTION_CACHE:
        return _STATIC_SELECTION_CACHE[key]

    native_capability = _native_capability(engine=engine, format=format)
    if native_capability.available:
        result = ("native", {"native": native_capability})
    else:
        wasm_capability = _wasm_capability(engine=engine, format=format)
        selected = "wasm" if wasm_capability.available else None
        result = (
            selected,
            {"native": native_capability, "wasm": wasm_capability},
        )
    _STATIC_SELECTION_CACHE[key] = result
    return result


def clear_capability_cache() -> None:
    """Clear cached backend probe results."""
    _CACHE.clear()
    _STATIC_CACHE.clear()
    _STATIC_SELECTION_CACHE.clear()


def available_backends(**kwargs) -> list[str]:
    """Return backend names whose runtime probe succeeds."""
    return [
        name
        for name, capability in capabilities(**kwargs).items()
        if capability.available
    ]
