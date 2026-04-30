from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from types import ModuleType
from urllib.request import urlopen

import pytest

import easydot
from easydot import _capabilities
from easydot import _html
from easydot import _native
from easydot import _server
from easydot._html import DEFAULT_CDN_URL


def _install_fake_marimo(monkeypatch, iframe_impl):
    marimo_module = ModuleType("marimo")
    output_module = ModuleType("marimo._output")
    formatting_module = ModuleType("marimo._output.formatting")
    runtime_module = ModuleType("marimo._runtime")
    context_module = ModuleType("marimo._runtime.context")
    formatting_module.iframe = iframe_impl
    context_module.runtime_context_installed = lambda: True

    monkeypatch.setitem(sys.modules, "marimo", marimo_module)
    monkeypatch.setitem(sys.modules, "marimo._output", output_module)
    monkeypatch.setitem(sys.modules, "marimo._output.formatting", formatting_module)
    monkeypatch.setitem(sys.modules, "marimo._runtime", runtime_module)
    monkeypatch.setitem(sys.modules, "marimo._runtime.context", context_module)


def test_asset_urls_serves_bundled_module():
    urls = easydot.asset_urls()

    assert urls["js"].startswith("http://127.0.0.1:")
    with urlopen(urls["js"], timeout=5) as response:
        body = response.read().decode("utf-8")

    assert response.status == 200
    assert "Graphviz" in body
    assert "export" in body


def test_html_uses_local_module_url():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="local")

    assert "http://127.0.0.1:" in rendered
    assert "Graphviz.load" in rendered
    assert "digraph { A -> B }" not in rendered


def test_html_accepts_pydot_like_object():
    class Graph:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    rendered = easydot.html(Graph(), backend="browser", source="cdn")

    assert "Graphviz.load" in rendered
    assert "digraph { A -> B }" not in rendered


def test_display_accepts_pydot_like_object():
    class Graph:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    obj = easydot.display(Graph(), source="cdn")

    assert repr(obj) == "digraph { A -> B }"
    assert "Graphviz.load" in obj._body_html()


def test_html_rejects_unsupported_dot_input():
    with pytest.raises(TypeError, match="DOT string or an object with a to_string"):
        easydot.html(object(), backend="browser", source="cdn")


def test_html_rejects_non_string_to_string_result():
    class Graph:
        def to_string(self):
            return b"digraph { A -> B }"

    with pytest.raises(TypeError, match=r"dot\.to_string\(\) must return a string"):
        easydot.html(Graph(), backend="browser", source="cdn")


def test_html_auto_includes_local_fallback_after_cdn_url():
    rendered = easydot.html("digraph { A -> B }", backend="browser")

    assert "http://127.0.0.1:" in rendered
    assert DEFAULT_CDN_URL in rendered
    assert rendered.index(DEFAULT_CDN_URL) < rendered.index("http://127.0.0.1:")
    assert "for (const url of moduleUrls)" in rendered


def test_html_shares_graphviz_instance_across_renders():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn")

    assert "globalThis.__easydot__" in rendered
    assert "graphvizCache" in rendered
    assert "cache.get(url)" in rendered
    assert "cache.delete(url)" in rendered


def test_asset_server_registers_shutdown_once_after_restart(monkeypatch):
    _server.shutdown_server()
    register_calls = []
    monkeypatch.setattr(_server, "_ATEXIT_REGISTERED", False)
    monkeypatch.setattr(_server.atexit, "register", lambda fn: register_calls.append(fn))

    _server.asset_base_url()
    _server.shutdown_server()
    _server.asset_base_url()
    _server.shutdown_server()

    assert register_calls == [_server.shutdown_server]


def test_html_cdn_source_avoids_local_url():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn")

    assert DEFAULT_CDN_URL in rendered
    assert "http://127.0.0.1:" not in rendered


def test_html_auto_source_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "cdn")

    rendered = easydot.html("digraph { A -> B }", backend="browser")

    assert DEFAULT_CDN_URL in rendered
    assert "http://127.0.0.1:" not in rendered


def test_html_explicit_source_wins_over_env(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "cdn")

    rendered = easydot.html("digraph { A -> B }", backend="browser", source="local")

    assert "http://127.0.0.1:" in rendered
    assert DEFAULT_CDN_URL not in rendered


def test_html_rejects_invalid_env_source(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "offline")

    with pytest.raises(ValueError, match="source must be 'auto', 'local', or 'cdn'"):
        easydot.html("digraph { A -> B }", backend="browser")


def test_display_exposes_rich_reprs():
    obj = easydot.display("digraph { A -> B }")

    assert obj._repr_html_()
    mime, payload = obj._mime_()
    assert mime == "text/html"
    assert payload
    bundle = obj._repr_mimebundle_()
    assert bundle.keys() == {mime}
    assert "Graphviz.load" in bundle[mime]
    assert repr(obj) == "digraph { A -> B }"


def test_display_publishes_html_in_ipython(monkeypatch):
    published = []
    ipython_module = ModuleType("IPython")
    display_module = ModuleType("IPython.display")
    display_module.display_html = lambda html, raw=False: published.append((html, raw))

    monkeypatch.setitem(sys.modules, "IPython", ipython_module)
    monkeypatch.setitem(sys.modules, "IPython.display", display_module)

    easydot.display("digraph { A -> B }")._ipython_display_()

    assert len(published) == 1
    html, raw = published[0]
    assert raw is True
    assert "<iframe" in html
    assert "width='100%' frameborder='0'" in html
    assert "digraph { A -> B }" not in html


def test_html_defaults_omit_fit_and_scale():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn")

    assert 'const fit = "none";' in rendered
    assert "const scale = 1.0;" in rendered


def test_html_defaults_to_disabled_worker_mode():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn")

    assert 'const workerMode = "disabled";' in rendered
    assert "const showSpinner = true;" in rendered
    assert "easydot-spinner" in rendered
    assert 'showStatus(message, state, false);' in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered


def test_html_spinner_false_disables_spinner_icon():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", spinner=False)

    assert "const showSpinner = false;" in rendered
    assert "showSpinner ? '<span class=\"easydot-spinner\"" in rendered


def test_html_worker_auto_tries_worker_with_fallback():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", worker="auto")

    assert 'const workerMode = "auto";' in rendered
    assert "new Worker(url, { type: \"module\" })" in rendered
    assert "Web Worker unavailable; rendering on main thread." in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered
    assert 'showStatus(message, state, false);' in rendered


def test_html_worker_true_requires_worker():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", worker=True)

    assert 'const workerMode = "require";' in rendered
    assert "Web Worker rendering was required but failed" in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered


def test_html_worker_false_disables_worker():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", worker=False)

    assert 'const workerMode = "disabled";' in rendered
    assert 'showStatus(message, state, false);' in rendered


def test_html_rejects_unknown_worker_value():
    with pytest.raises(ValueError, match="worker must be 'auto', True, or False"):
        easydot.html("digraph { A -> B }", backend="browser", source="cdn", worker="require")


def test_html_fit_true_enables_both_mode():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", fit=True, scale=1.5)

    assert 'const fit = "both";' in rendered
    assert "const scale = 1.5;" in rendered
    assert 'class="easydot-fit-both"' in rendered
    assert ".easydot-fit-both > svg" in rendered
    assert "aspect-ratio:var(--easydot-nat-w) / var(--easydot-nat-h)" in rendered
    assert "html,body{margin:0;padding:0;height:100%;overflow:hidden}" in rendered
    assert "svgEl.style.transform" not in rendered


def test_html_fit_horizontal_uses_css_responsiveness():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", fit="horizontal", scale=1.5)

    assert 'const fit = "horizontal";' in rendered
    assert 'class="easydot-fit-horizontal"' in rendered
    assert ".easydot-fit-horizontal > svg{width:100%;height:auto;" in rendered
    assert (
        "max-width:calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px)"
        in rendered
    )
    assert "const setupEasydotFit = (target, fit, scale, observe = true)" in rendered
    assert "observer.observe(svgEl)" in rendered
    assert 'setupEasydotFit(target, fit, scale)' in rendered


def test_html_fit_vertical_uses_flex_viewport():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", fit="vertical")

    assert 'const fit = "vertical";' in rendered
    assert 'class="easydot-fit-vertical"' in rendered
    assert ".easydot-fit-vertical{overflow-x:auto;overflow-y:hidden}" in rendered
    assert "display:flex;flex-direction:column" in rendered
    assert (
        "max-height:calc(var(--easydot-nat-h) * var(--easydot-scale) * 1px)"
        in rendered
    )
    assert "html,body{margin:0;padding:0;height:100%;overflow:hidden}" in rendered


def test_html_viewport_fits_skip_frame_height_sync():
    for fit in ("vertical", "both"):
        rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", fit=fit)
        assert "if (observe && !isViewportFit)" in rendered
        assert 'setupEasydotFit(target, "none", 1, false)' in rendered
        assert "syncFrameHeight" in rendered


def test_html_rejects_unknown_fit_value():
    with pytest.raises(ValueError):
        easydot.html("digraph { A -> B }", backend="browser", source="cdn", fit="diagonal")


def test_html_scale_without_fit_adds_scaled_class_via_js():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", scale=2.0)

    assert 'class="easydot-fit-none"' in rendered
    assert "const scale = 2.0;" in rendered
    assert 'target.classList.add("easydot-scaled")' in rendered
    assert ".easydot-fit-none.easydot-scaled > svg" in rendered
    assert (
        "width:calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px)"
        in rendered
    )
    assert "svgEl.width && svgEl.width.baseVal" in rendered
    assert "svgEl.style.transform" not in rendered


def test_html_default_includes_toolbar():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn")

    assert "data-easydot-toolbar" in rendered
    assert "data-easydot-copy" in rendered
    assert "data-easydot-download" in rendered
    assert "navigator.clipboard.writeText(svg)" in rendered
    assert "new Blob([svg]" in rendered
    assert "position:sticky" in rendered


def test_html_toolbar_false_omits_toolbar():
    rendered = easydot.html("digraph { A -> B }", backend="browser", source="cdn", toolbar=False)

    assert "data-easydot-toolbar" not in rendered
    assert "data-easydot-copy" not in rendered
    assert "data-easydot-download" not in rendered


def test_display_propagates_toolbar_flag():
    obj = easydot.display("digraph { A -> B }", source="cdn", toolbar=False)

    assert obj.toolbar is False
    assert "data-easydot-toolbar" not in obj._body_html()

    default_obj = easydot.display("digraph { A -> B }", source="cdn")
    assert default_obj.toolbar is True
    assert "data-easydot-toolbar" in default_obj._body_html()


def test_display_propagates_worker_flag():
    obj = easydot.display("digraph { A -> B }", source="cdn", worker=True)

    assert obj.worker is True
    assert 'const workerMode = "require";' in obj._body_html()


def test_display_propagates_spinner_flag():
    obj = easydot.display("digraph { A -> B }", source="cdn", spinner=False)

    assert obj.spinner is False
    assert "const showSpinner = false;" in obj._body_html()


@pytest.mark.skipif(
    importlib.util.find_spec("marimo") is None,
    reason="marimo not installed",
)
def test_display_managed_iframe_integrates_with_real_marimo():
    mime, payload = easydot.display(
        "digraph { A -> B }",
        source="cdn",
        fit=True,
        scale=1.25,
        iframe_mode="managed",
    )._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "srcdoc" in payload
    assert "Graphviz.load" in payload


@pytest.mark.skipif(
    importlib.util.find_spec("marimo") is None,
    reason="marimo not installed",
)
def test_marimo_export_html_contains_easydot_payload(tmp_path):
    notebook = tmp_path / "marimo_export_smoke.py"
    output = tmp_path / "marimo_export_smoke.html"
    notebook.write_text(
        textwrap.dedent(
            """
            import marimo

            app = marimo.App()

            @app.cell
            def _():
                import easydot
                return (easydot,)

            @app.cell
            def _(easydot):
                easydot.display("digraph { A -> B }", fit=True, spinner=False)
                return

            if __name__ == "__main__":
                app.run()
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "marimo",
            "export",
            "html",
            str(notebook),
            "-o",
            str(output),
            "-f",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    exported = output.read_text(encoding="utf-8")
    assert "\\u003Ciframe srcdoc=" in exported
    assert "onload='__resizeIframe(this)'" in exported
    assert "const showSpinner = false;" in exported
    assert 'const workerMode = \\u0026quot;disabled\\u0026quot;;' in exported


def test_display_iframe_false_skips_iframe_wrapping(monkeypatch):
    _install_fake_marimo(monkeypatch, lambda *_args, **_kwargs: pytest.fail("marimo iframe should not be used"))
    monkeypatch.setitem(sys.modules, "IPython", ModuleType("IPython"))

    obj = easydot.display("digraph { A -> B }", source="cdn", iframe=False)

    mime, payload = obj._mime_()
    assert mime == "text/html"
    assert "<iframe" not in payload
    assert "Graphviz" in payload
    assert "<iframe" not in obj._repr_html_()

    published = []
    display_module = ModuleType("IPython.display")
    display_module.display_html = lambda html, raw=False: published.append((html, raw))
    monkeypatch.setitem(sys.modules, "IPython.display", display_module)
    obj._ipython_display_()

    assert len(published) == 1
    html, _raw = published[0]
    assert "<iframe" not in html


def test_display_srcdoc_iframe_mode_bypasses_marimo_iframe(monkeypatch):
    _install_fake_marimo(monkeypatch, lambda *_args, **_kwargs: pytest.fail("marimo iframe should not be used"))
    monkeypatch.setenv("EASYDOT_IFRAME_MODE", "srcdoc")

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "srcdoc=" in payload
    assert DEFAULT_CDN_URL in payload


def test_display_auto_does_not_use_managed_iframe_without_runtime(monkeypatch):
    iframe_calls = []

    class _Frame:
        def _mime_(self):
            return "text/html", '<iframe srcdoc="<p>ok</p>" height="400px"></iframe>'

    def iframe_impl(*_args, **kwargs):
        iframe_calls.append(kwargs)
        return _Frame()

    _install_fake_marimo(monkeypatch, iframe_impl)

    from marimo._runtime import context

    context.runtime_context_installed = lambda: False

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "srcdoc=" in payload
    assert "Graphviz.load" in payload
    assert iframe_calls == []


def test_display_auto_iframe_wraps_without_ipython_or_marimo_runtime(monkeypatch):
    monkeypatch.delitem(sys.modules, "IPython", raising=False)
    monkeypatch.delitem(sys.modules, "marimo", raising=False)
    monkeypatch.delitem(sys.modules, "marimo._output", raising=False)
    monkeypatch.delitem(sys.modules, "marimo._output.formatting", raising=False)
    monkeypatch.delitem(sys.modules, "marimo._runtime", raising=False)
    monkeypatch.delitem(sys.modules, "marimo._runtime.context", raising=False)

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "srcdoc=" in payload
    assert "Graphviz.load" in payload


def test_display_data_iframe_mode_bypasses_marimo_iframe(monkeypatch):
    _install_fake_marimo(
        monkeypatch,
        lambda *_args, **_kwargs: pytest.fail("marimo iframe should not be used"),
    )
    monkeypatch.setenv("EASYDOT_IFRAME_MODE", "data")

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "src='data:text/html;charset=utf-8;base64," in payload
    assert "srcdoc=" not in payload
    assert "digraph { A -> B }" not in payload


def test_display_iframe_mode_argument_uses_data_iframe(monkeypatch):
    _install_fake_marimo(
        monkeypatch,
        lambda *_args, **_kwargs: pytest.fail("marimo iframe should not be used"),
    )

    mime, payload = easydot.display(
        "digraph { A -> B }",
        source="cdn",
        iframe_mode="data",
    )._mime_()

    assert mime == "text/html"
    assert "src='data:text/html;charset=utf-8;base64," in payload
    assert "srcdoc=" not in payload


def test_display_iframe_mode_argument_wins_over_env(monkeypatch):
    monkeypatch.setenv("EASYDOT_IFRAME_MODE", "data")

    mime, payload = easydot.display(
        "digraph { A -> B }",
        source="cdn",
        iframe_mode="srcdoc",
    )._mime_()

    assert mime == "text/html"
    assert "srcdoc=" in payload
    assert "src='data:text/html;charset=utf-8;base64," not in payload


def test_display_auto_uses_data_iframe_in_pycharm(monkeypatch):
    _install_fake_marimo(
        monkeypatch,
        lambda *_args, **_kwargs: pytest.fail("marimo iframe should not be used"),
    )
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "src='data:text/html;charset=utf-8;base64," in payload
    assert "srcdoc=" not in payload


def test_display_explicit_srcdoc_wins_in_pycharm(monkeypatch):
    monkeypatch.setenv("PYCHARM_HOSTED", "1")
    monkeypatch.setenv("EASYDOT_IFRAME_MODE", "srcdoc")

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert "srcdoc=" in payload
    assert "src='data:text/html;charset=utf-8;base64," not in payload


def test_display_rejects_invalid_iframe_mode(monkeypatch):
    monkeypatch.setenv("EASYDOT_IFRAME_MODE", "file")

    message = "EASYDOT_IFRAME_MODE must be 'auto', 'managed', 'srcdoc', or 'data'"
    with pytest.raises(ValueError, match=message):
        easydot.display("digraph { A -> B }", source="cdn")._mime_()


def test_display_rejects_invalid_iframe_mode_argument():
    message = "iframe_mode must be 'auto', 'managed', 'srcdoc', or 'data'"
    with pytest.raises(ValueError, match=message):
        easydot.display("digraph { A -> B }", source="cdn", iframe_mode="file")
    with pytest.raises(ValueError, match=message):
        easydot.display("digraph { A -> B }", source="cdn", iframe_mode="marimo")


def test_display_mime_uses_managed_iframe_without_default_height(monkeypatch):
    expected = '<iframe srcdoc="<p>ok</p>"></iframe>'
    iframe_calls = []

    class _Frame:
        def _mime_(self):
            return "text/html", expected

    def iframe_impl(*_args, **kwargs):
        iframe_calls.append(kwargs)
        return _Frame()

    _install_fake_marimo(monkeypatch, iframe_impl)

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert payload == expected
    assert iframe_calls == [{}]


def test_display_auto_uses_managed_iframe_with_runtime(monkeypatch):
    expected = '<iframe srcdoc="<p>ok</p>"></iframe>'
    iframe_calls = []

    class _Frame:
        def _mime_(self):
            return "text/html", expected

    def iframe_impl(*_args, **kwargs):
        iframe_calls.append(kwargs)
        return _Frame()

    _install_fake_marimo(monkeypatch, iframe_impl)

    from marimo._runtime import context

    context.runtime_context_installed = lambda: True

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert payload == expected
    assert iframe_calls == [{}]


def test_display_fit_modes_do_not_force_iframe_height(monkeypatch):
    iframe_calls = []

    class _Frame:
        def _mime_(self):
            return "text/html", "<iframe></iframe>"

    def iframe_impl(*_args, **kwargs):
        iframe_calls.append(kwargs)
        return _Frame()

    _install_fake_marimo(monkeypatch, iframe_impl)

    for fit in ("vertical", True):
        easydot.display("digraph { A -> B }", source="cdn", fit=fit)._mime_()

    assert iframe_calls == [{}, {}]


def test_display_explicit_iframe_height_is_forwarded(monkeypatch):
    iframe_calls = []

    class _Frame:
        def _mime_(self):
            return "text/html", "<iframe></iframe>"

    def iframe_impl(*_args, **kwargs):
        iframe_calls.append(kwargs)
        return _Frame()

    _install_fake_marimo(monkeypatch, iframe_impl)

    obj = easydot.display("digraph { A -> B }", source="cdn", iframe_height="320px")
    obj._mime_()

    assert iframe_calls == [{"height": "320px"}]


def test_svg_renders_valid_svg():
    svg_text = easydot.svg("digraph { A -> B }")

    assert ("<svg" in svg_text or "<?xml" in svg_text) and "A" in svg_text


def test_svg_accepts_pydot_like_object():
    class Graph:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    svg_text = easydot.svg(Graph())

    assert "<svg" in svg_text or "<?xml" in svg_text


def test_display_svg_returns_svg_display():
    obj = easydot.display_svg("digraph { A -> B }")

    assert isinstance(obj, easydot.SvgDisplay)


def test_svg_display_mimebundle_contains_svg():
    obj = easydot.SvgDisplay("digraph { A -> B }")
    bundle = obj._repr_mimebundle_()

    assert "image/svg+xml" in bundle
    assert "text/html" in bundle
    assert "<svg" in bundle["image/svg+xml"] or "<?xml" in bundle["image/svg+xml"]


def test_svg_display_repr_svg_returns_svg():
    obj = easydot.SvgDisplay("digraph { A -> B }")
    svg_text = obj._repr_svg_()

    assert "<svg" in svg_text or "<?xml" in svg_text


def test_svg_display_repr_returns_dot():
    obj = easydot.SvgDisplay("digraph { A -> B }")

    assert repr(obj) == "digraph { A -> B }"


def test_native_svg_runs_graphviz_executable(monkeypatch):
    calls = []

    def fake_run(args, *, input, stdout, stderr, check):
        calls.append((args, input, stdout, stderr, check))
        return subprocess.CompletedProcess(args, 0, b"<svg>A</svg>", b"")

    monkeypatch.setattr(_native.subprocess, "run", fake_run)

    assert easydot.native_svg("digraph { A -> B }", engine="neato") == "<svg>A</svg>"
    assert calls == [
        (
            ["neato", "-Tsvg"],
            b"digraph { A -> B }",
            subprocess.PIPE,
            subprocess.PIPE,
            False,
        )
    ]


def test_native_accepts_pydot_like_object(monkeypatch):
    class Graph:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    monkeypatch.setattr(
        _native.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, b"plain", b""),
    )

    assert easydot.native(Graph(), format="plain") == "plain"


def test_native_missing_executable_raises_helpful_error(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError("dot")

    monkeypatch.setattr(_native.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Native Graphviz executable 'dot' was not found"):
        easydot.native_svg("digraph { A -> B }")


def test_native_failure_includes_stderr(monkeypatch):
    monkeypatch.setattr(
        _native.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, b"", b"syntax error"),
    )

    with pytest.raises(RuntimeError, match="syntax error"):
        easydot.native_svg("digraph {")


def test_display_native_svg_returns_native_svg_display():
    obj = easydot.display_native_svg("digraph { A -> B }")

    assert isinstance(obj, easydot.NativeSvgDisplay)
    assert repr(obj) == "digraph { A -> B }"


def test_native_svg_display_mimebundle_contains_svg(monkeypatch):
    monkeypatch.setattr(_native, "native", lambda dot, *, engine="dot", format="svg": "<svg>A</svg>")

    bundle = easydot.NativeSvgDisplay("digraph { A -> B }")._repr_mimebundle_()

    assert "image/svg+xml" in bundle
    assert "text/html" in bundle
    assert bundle["image/svg+xml"] == "<svg>A</svg>"


def test_svg_missing_dependency_raises_helpful_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "wasi_graphviz", None)

    with pytest.raises(ImportError, match="wasi-graphviz"):
        easydot.svg("digraph { A -> B }")


def test_svg_display_missing_dependency_raises_helpful_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "wasi_graphviz", None)

    with pytest.raises(ImportError, match="wasi-graphviz"):
        easydot.SvgDisplay("digraph { A -> B }")._repr_svg_()


def test_render_browser_returns_graph():
    obj = easydot.render("digraph { A -> B }", backend="browser")

    assert isinstance(obj, easydot.Graph)
    assert obj.backend == "browser"


def test_render_wasm_returns_graph():
    obj = easydot.render("digraph { A -> B }", backend="wasm")

    assert isinstance(obj, easydot.Graph)
    assert obj.backend == "wasm"


def test_render_native_returns_graph():
    obj = easydot.render("digraph { A -> B }", backend="native")

    assert isinstance(obj, easydot.Graph)
    assert obj.backend == "native"


def test_render_auto_prefers_native(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", True),
            "native": easydot.BackendCapability("native", True),
        },
    )

    obj = easydot.render("digraph { A -> B }", backend="auto")

    assert isinstance(obj, easydot.Graph)
    assert obj._resolve_backend() == "native"


def test_render_auto_falls_back_to_wasm(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", True),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )

    obj = easydot.render("digraph { A -> B }", backend="auto")

    assert isinstance(obj, easydot.Graph)
    assert obj._resolve_backend() == "wasm"


def test_render_auto_prefers_browser_local_before_cdn(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )

    obj = easydot.render("digraph { A -> B }", backend="auto")
    assert obj._resolve_backend() == "browser"
    assert obj.source == "local"


def test_render_auto_uses_browser_cdn_when_local_unavailable(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": False, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )

    obj = easydot.render("digraph { A -> B }", backend="auto")
    assert obj._resolve_backend() == "browser"
    assert obj.source == "cdn"


def test_render_auto_honors_explicit_browser_source(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )

    obj = easydot.render("digraph { A -> B }", backend="auto", source="cdn")
    assert obj._resolve_backend() == "browser"
    assert obj.source == "cdn"


def test_render_auto_forwards_capability_options_only_to_probe(monkeypatch):
    calls = []

    def fake_capabilities(**kwargs):
        calls.append(kwargs)
        return {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": False}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        }

    monkeypatch.setattr(easydot, "capabilities", fake_capabilities)

    obj = easydot.render(
        "digraph { A -> B }",
        backend="auto",
        engine="neato",
        capability_timeout=0.1,
        check_cdn=False,
    )
    obj._resolve_backend()  # trigger probe

    assert calls == [{"engine": "neato", "timeout": 0.1, "check_cdn": False, "refresh": False}]
    assert obj.source == "local"
    assert obj.engine == "neato"


def test_render_auto_can_refresh_capability_cache(monkeypatch):
    calls = []

    def fake_capabilities(**kwargs):
        calls.append(kwargs)
        return {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": False}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        }

    monkeypatch.setattr(easydot, "capabilities", fake_capabilities)

    obj = easydot.render("digraph { A -> B }", backend="auto", refresh_capabilities=True)
    obj._resolve_backend()  # trigger probe

    assert calls == [{"engine": "dot", "timeout": 2.0, "check_cdn": True, "refresh": True}]


def test_render_auto_raises_when_no_backend_is_available(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability(
                "browser", False, "offline", details={"local": False, "cdn": False}
            ),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )

    with pytest.raises(RuntimeError, match="no easydot backend is available"):
        easydot.render("digraph { A -> B }", backend="auto")._resolve_backend()


def test_render_forwards_kwargs():
    obj = easydot.render("digraph { A -> B }", backend="browser", source="cdn")

    assert isinstance(obj, easydot.Graph)
    assert DEFAULT_CDN_URL in obj._body_html()


def test_render_rejects_unknown_backend():
    with pytest.raises(ValueError, match="backend must be 'auto', 'browser', 'wasm', or 'native'"):
        easydot.render("digraph { A -> B }", backend="missing")


def test_to_string_browser_returns_html():
    with pytest.warns(DeprecationWarning):
        result = easydot.to_string("digraph { A -> B }", backend="browser")

    assert "<" in result
    assert isinstance(result, str)


def test_to_string_wasm_returns_svg():
    with pytest.warns(DeprecationWarning):
        result = easydot.to_string("digraph { A -> B }", backend="wasm")

    assert ("<svg" in result or "<?xml" in result) and isinstance(result, str)


def test_to_string_native_returns_svg(monkeypatch):
    monkeypatch.setattr(_native, "native_svg", lambda dot, *, engine="dot": "<svg>A</svg>")

    with pytest.warns(DeprecationWarning):
        result = easydot.to_string("digraph { A -> B }", backend="native")

    assert result == "<svg>A</svg>"


def test_to_string_auto_uses_selected_backend(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": False}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )
    monkeypatch.setattr(_html, "html", lambda dot, **kwargs: f"source={kwargs['source']}")

    with pytest.warns(DeprecationWarning):
        result = easydot.to_string("digraph { A -> B }", backend="auto")

    assert result == "source=local"


def test_to_string_rejects_unknown_backend():
    with pytest.raises(ValueError, match="backend must be 'auto', 'browser', 'wasm', or 'native'"):
        easydot.to_string("digraph { A -> B }", backend="missing")


def test_capabilities_reports_available_backends(monkeypatch):
    _capabilities.clear_capability_cache()
    monkeypatch.setattr(
        _capabilities,
        "_browser_capability",
        lambda *, timeout, check_cdn: easydot.BackendCapability(
            "browser", True, details={"local": True, "cdn": False}
        ),
    )
    monkeypatch.setattr(
        _capabilities,
        "_wasm_capability",
        lambda *, engine: easydot.BackendCapability("wasm", True, details={"engine": engine}),
    )
    monkeypatch.setattr(
        _capabilities,
        "_native_capability",
        lambda *, engine: easydot.BackendCapability("native", False, "missing"),
    )

    caps = easydot.capabilities(engine="neato", timeout=0.5, check_cdn=False)

    assert caps.keys() == {"browser", "wasm", "native"}
    assert caps["browser"].available is True
    assert caps["wasm"].details == {"engine": "neato"}
    assert caps["native"].available is False
    assert easydot.available_backends(engine="neato", timeout=0.5, check_cdn=False) == [
        "browser",
        "wasm",
    ]


def test_capabilities_caches_probe_results(monkeypatch):
    _capabilities.clear_capability_cache()
    calls = []

    def fake_browser_capability(*, timeout, check_cdn):
        calls.append(("browser", timeout, check_cdn))
        return easydot.BackendCapability("browser", True, details={"local": True, "cdn": False})

    def fake_wasm_capability(*, engine):
        calls.append(("wasm", engine))
        return easydot.BackendCapability("wasm", False, "runtime")

    def fake_native_capability(*, engine):
        calls.append(("native", engine))
        return easydot.BackendCapability("native", False, "missing")

    monkeypatch.setattr(_capabilities, "_browser_capability", fake_browser_capability)
    monkeypatch.setattr(_capabilities, "_wasm_capability", fake_wasm_capability)
    monkeypatch.setattr(_capabilities, "_native_capability", fake_native_capability)

    first = easydot.capabilities(engine="dot", timeout=0.5, check_cdn=False)
    second = easydot.capabilities(engine="dot", timeout=0.5, check_cdn=False)

    assert first is second
    assert calls == [
        ("browser", 0.5, False),
        ("wasm", "dot"),
        ("native", "dot"),
    ]


def test_capabilities_refresh_bypasses_cache(monkeypatch):
    _capabilities.clear_capability_cache()
    calls = []

    monkeypatch.setattr(
        _capabilities,
        "_browser_capability",
        lambda *, timeout, check_cdn: calls.append("browser")
        or easydot.BackendCapability("browser", True, details={"local": True, "cdn": False}),
    )
    monkeypatch.setattr(
        _capabilities,
        "_wasm_capability",
        lambda *, engine: calls.append("wasm") or easydot.BackendCapability("wasm", False),
    )
    monkeypatch.setattr(
        _capabilities,
        "_native_capability",
        lambda *, engine: calls.append("native") or easydot.BackendCapability("native", False),
    )

    easydot.capabilities(engine="dot", timeout=0.5, check_cdn=False)
    easydot.capabilities(engine="dot", timeout=0.5, check_cdn=False, refresh=True)

    assert calls == ["browser", "wasm", "native", "browser", "wasm", "native"]


def test_browser_capability_checks_local_and_cdn_sources(monkeypatch):
    monkeypatch.setattr(_capabilities, "asset_urls", lambda: {"js": "http://local/module.js"})

    calls = []

    def fake_probe(url, *, timeout):
        calls.append((url, timeout))
        if url == "http://local/module.js":
            return True, None
        return False, "offline"

    monkeypatch.setattr(_capabilities, "_probe_url", fake_probe)

    capability = _capabilities._browser_capability(timeout=0.25, check_cdn=True)

    assert capability.available is True
    assert capability.details["local"] is True
    assert capability.details["cdn"] is False
    assert capability.details["cdn_reason"] == "offline"
    assert calls == [
        ("http://local/module.js", 0.25),
        (_capabilities.DEFAULT_CDN_URL, 0.25),
    ]


def test_browser_capability_reports_source_failures(monkeypatch):
    monkeypatch.setattr(_capabilities, "asset_urls", lambda: {"js": "http://local/module.js"})
    monkeypatch.setattr(_capabilities, "_probe_url", lambda url, *, timeout: (False, "blocked"))

    capability = _capabilities._browser_capability(timeout=0.25, check_cdn=True)

    assert capability.available is False
    assert "neither local browser assets nor CDN assets" in capability.reason
    assert capability.details["local_reason"] == "blocked"
    assert capability.details["cdn_reason"] == "blocked"


def test_browser_capability_can_skip_cdn_check(monkeypatch):
    monkeypatch.setattr(_capabilities, "asset_urls", lambda: {"js": "http://local/module.js"})
    monkeypatch.setattr(_capabilities, "_probe_url", lambda url, *, timeout: (True, None))

    capability = _capabilities._browser_capability(timeout=0.25, check_cdn=False)

    assert capability.available is True
    assert capability.details["local"] is True
    assert capability.details["cdn"] is False
    assert capability.details["cdn_reason"] == "not checked"


def test_wasm_capability_renders_probe_instead_of_only_checking_import(monkeypatch):
    calls = []

    def fake_svg(dot, *, engine):
        calls.append((dot, engine))
        return "<svg></svg>"

    monkeypatch.setattr(_capabilities, "svg", fake_svg)

    capability = _capabilities._wasm_capability(engine="dot")

    assert capability.available is True
    assert calls == [(_capabilities._PROBE_DOT, "dot")]


def test_wasm_capability_reports_runtime_failure(monkeypatch):
    def fake_svg(dot, *, engine):
        raise RuntimeError("WASI runtime unavailable")

    monkeypatch.setattr(_capabilities, "svg", fake_svg)

    capability = _capabilities._wasm_capability(engine="dot")

    assert capability.available is False
    assert capability.reason == "RuntimeError: WASI runtime unavailable"


def test_native_capability_renders_probe_instead_of_only_checking_executable(monkeypatch):
    calls = []

    def fake_native_svg(dot, *, engine):
        calls.append((dot, engine))
        return "<?xml version='1.0'?><svg></svg>"

    monkeypatch.setattr(_capabilities, "native_svg", fake_native_svg)

    capability = _capabilities._native_capability(engine="neato")

    assert capability.available is True
    assert capability.details == {"engine": "neato"}
    assert calls == [(_capabilities._PROBE_DOT, "neato")]


def test_native_capability_reports_subprocess_failure(monkeypatch):
    def fake_native_svg(dot, *, engine):
        raise RuntimeError("Native Graphviz executable 'dot' was not found")

    monkeypatch.setattr(_capabilities, "native_svg", fake_native_svg)

    capability = _capabilities._native_capability(engine="dot")

    assert capability.available is False
    assert capability.reason == "RuntimeError: Native Graphviz executable 'dot' was not found"
    assert capability.details == {"engine": "dot"}


# ---------- New API tests ----------

def test_html_wasm_includes_fit_classes():
    result = easydot.html("digraph { A -> B }", backend="wasm", fit="horizontal")

    assert "easydot-fit-horizontal" in result
    assert "--easydot-nat-w:" in result
    assert "--easydot-nat-h:" in result
    assert "data-easydot-toolbar" in result


def test_html_native_matches_wasm_wrapper_structure(monkeypatch):
    svg_stub = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 134 116" width="134pt" height="116pt"></svg>'
    monkeypatch.setattr(_native, "native", lambda dot, *, engine="dot", format="svg": svg_stub)

    result = easydot.html("digraph { A -> B }", backend="native", fit="horizontal")

    assert "easydot-fit-horizontal" in result
    assert "--easydot-nat-w:178.6667" in result
    assert "--easydot-nat-h:154.6667" in result


def test_html_static_backend_rejects_browser_source():
    import pytest
    with pytest.raises(TypeError, match="source is only supported by backend='browser'"):
        easydot.html("digraph { A -> B }", backend="wasm", source="cdn")


def test_html_static_backend_rejects_worker():
    import pytest
    with pytest.raises(TypeError, match="worker is only supported by backend='browser'"):
        easydot.html("digraph { A -> B }", backend="wasm", worker=True)


def test_extract_viewbox_handles_negative_origin():
    from easydot._display import extract_viewbox
    svg = '<svg viewBox="-4 -4 138 124"></svg>'
    w, h = extract_viewbox(svg)
    assert w == 138.0
    assert h == 124.0


def test_extract_viewbox_uses_css_pixel_dimensions():
    from easydot._display import extract_viewbox
    svg = '<svg width="134pt" height="116pt" viewBox="0 0 134 116"></svg>'
    w, h = extract_viewbox(svg)
    assert w == pytest.approx(178.6667)
    assert h == pytest.approx(154.6667)


def test_inline_svg_strips_xml_prolog_and_doctype():
    from easydot._display import inline_svg
    raw = '<?xml version="1.0"?><!DOCTYPE svg PUBLIC "...">\n<!-- comment -->\n<svg viewBox="0 0 10 10" width="10pt" height="10pt"><g/></svg>'
    result = inline_svg(raw)
    assert result.startswith("<svg")
    assert "<?xml" not in result
    assert "<!DOCTYPE" not in result
    assert 'width="100%"' in result
    assert 'height="100%"' in result
    assert 'viewBox="0 0 10 10"' in result


def test_svg_browser_backend_raises():
    with pytest.raises(ValueError, match="backend='browser' renders in the browser at view-time"):
        easydot.svg("digraph { A -> B }", backend="browser")


def test_svg_auto_skips_browser(monkeypatch):
    monkeypatch.setattr(
        easydot,
        "capabilities",
        lambda **kwargs: {
            "browser": easydot.BackendCapability("browser", True, details={"local": True, "cdn": True}),
            "wasm": easydot.BackendCapability("wasm", False, "runtime"),
            "native": easydot.BackendCapability("native", False, "missing"),
        },
    )
    with pytest.raises(RuntimeError, match="no SVG-producing backend is available"):
        easydot.svg("digraph { A -> B }", backend="auto")


def test_native_binary_format_returns_bytes(monkeypatch):
    fake_png = b"\x89PNG\r\n\x1a\n"
    monkeypatch.setattr(
        _native.subprocess,
        "run",
        lambda *args, **kwargs: __import__("subprocess").CompletedProcess(args, 0, fake_png, b""),
    )
    result = easydot.native("digraph { A -> B }", format="png")
    assert isinstance(result, bytes)
    assert result == fake_png


def test_to_string_emits_deprecation_warning():
    with pytest.warns(DeprecationWarning, match="to_string.*deprecated"):
        easydot.to_string("digraph { A -> B }", backend="wasm")


def test_static_toolbar_copy_button_present():
    result = easydot.html("digraph { A -> B }", backend="wasm", toolbar=True)
    assert "data-easydot-copy" in result
    assert "data-easydot-download" in result
    # SVG is inlined as base64 in a data-svg attribute
    assert "data-svg=" in result


def test_graph_repr_mimebundle_browser_omits_svg():
    obj = easydot.render("digraph { A -> B }", backend="browser")
    bundle = obj._repr_mimebundle_()
    assert "text/html" in bundle
    assert "image/svg+xml" not in bundle


def test_graph_repr_mimebundle_wasm_includes_html_and_svg():
    obj = easydot.render("digraph { A -> B }", backend="wasm")
    bundle = obj._repr_mimebundle_()
    assert "text/html" in bundle
    assert "image/svg+xml" in bundle


def test_static_viewport_fit_uses_iframe_with_default_height():
    obj = easydot.render("digraph { A -> B }", backend="wasm", fit="both")
    mime, payload = obj._mime_()
    assert mime == "text/html"
    assert "<iframe" in payload
    assert "height=" in payload


def test_deprecated_display_svg_emits_warning():
    with pytest.warns(DeprecationWarning):
        obj = easydot.display_svg("digraph { A -> B }")
    assert isinstance(obj, easydot.SvgDisplay)


def test_deprecated_display_native_svg_emits_warning():
    with pytest.warns(DeprecationWarning):
        obj = easydot.display_native_svg("digraph { A -> B }")
    assert isinstance(obj, easydot.NativeSvgDisplay)


def test_cli_fit_and_scale_forwarded(monkeypatch, capsys):
    from easydot._cli import main
    monkeypatch.setattr("sys.stdin", type("MockStdin", (), {"read": lambda: "digraph { A -> B }"}))
    monkeypatch.setattr("sys.argv", ["easydot", "--backend", "wasm", "--fit", "horizontal", "--scale", "1.5"])
    assert main() == 0
    captured = capsys.readouterr()
    assert "easydot-fit-horizontal" in captured.out
    assert "easydot-scaled" in captured.out
    assert "--easydot-scale:1.5000" in captured.out


def test_cli_format_svg_uses_svg_dispatcher(monkeypatch, capsys):
    from easydot._cli import main
    monkeypatch.setattr("sys.stdin", type("MockStdin", (), {"read": lambda: "digraph { A -> B }"}))
    monkeypatch.setattr("sys.argv", ["easydot", "--backend", "wasm", "--format", "svg"])
    assert main() == 0
    captured = capsys.readouterr()
    assert "<svg" in captured.out
    assert "easydot-fit" not in captured.out


def test_cli_format_png_returns_bytes_to_stdout(monkeypatch, capsys):
    from easydot._cli import main
    monkeypatch.setattr("sys.stdin", type("MockStdin", (), {"read": lambda: "digraph { A -> B }"}))
    monkeypatch.setattr("sys.argv", ["easydot", "--backend", "native", "--format", "png"])
    
    written_bytes = b""
    def mock_write(b):
        nonlocal written_bytes
        written_bytes += b
    
    monkeypatch.setattr("sys.stdout.buffer.write", mock_write)
    monkeypatch.setattr(_native.subprocess, "run", lambda *args, **kwargs: __import__("subprocess").CompletedProcess(args, 0, b"fake_png_data", b""))
    
    assert main() == 0
    assert written_bytes == b"fake_png_data"
