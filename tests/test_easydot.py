from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from types import ModuleType
from urllib.request import urlopen

import pytest

import easydot
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
    rendered = easydot.html("digraph { A -> B }", source="local")

    assert "http://127.0.0.1:" in rendered
    assert "Graphviz.load" in rendered
    assert "digraph { A -> B }" not in rendered


def test_html_accepts_pydot_like_object():
    class Graph:
        def to_string(self) -> str:
            return "digraph { A -> B }"

    rendered = easydot.html(Graph(), source="cdn")

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
        easydot.html(object(), source="cdn")


def test_html_rejects_non_string_to_string_result():
    class Graph:
        def to_string(self):
            return b"digraph { A -> B }"

    with pytest.raises(TypeError, match=r"dot\.to_string\(\) must return a string"):
        easydot.html(Graph(), source="cdn")


def test_html_auto_includes_local_fallback_after_cdn_url():
    rendered = easydot.html("digraph { A -> B }")

    assert "http://127.0.0.1:" in rendered
    assert DEFAULT_CDN_URL in rendered
    assert rendered.index(DEFAULT_CDN_URL) < rendered.index("http://127.0.0.1:")
    assert "for (const url of moduleUrls)" in rendered


def test_html_shares_graphviz_instance_across_renders():
    rendered = easydot.html("digraph { A -> B }", source="cdn")

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
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert DEFAULT_CDN_URL in rendered
    assert "http://127.0.0.1:" not in rendered


def test_html_auto_source_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "cdn")

    rendered = easydot.html("digraph { A -> B }")

    assert DEFAULT_CDN_URL in rendered
    assert "http://127.0.0.1:" not in rendered


def test_html_explicit_source_wins_over_env(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "cdn")

    rendered = easydot.html("digraph { A -> B }", source="local")

    assert "http://127.0.0.1:" in rendered
    assert DEFAULT_CDN_URL not in rendered


def test_html_rejects_invalid_env_source(monkeypatch):
    monkeypatch.setenv("EASYDOT_SOURCE", "offline")

    with pytest.raises(ValueError, match="source must be 'auto', 'local', or 'cdn'"):
        easydot.html("digraph { A -> B }")


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
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert 'const fit = "none";' in rendered
    assert "const scale = 1.0;" in rendered


def test_html_defaults_to_disabled_worker_mode():
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert 'const workerMode = "disabled";' in rendered
    assert "const showSpinner = true;" in rendered
    assert "easydot-spinner" in rendered
    assert 'showStatus(message, state, false);' in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered


def test_html_spinner_false_disables_spinner_icon():
    rendered = easydot.html("digraph { A -> B }", source="cdn", spinner=False)

    assert "const showSpinner = false;" in rendered
    assert "showSpinner ? '<span class=\"easydot-spinner\"" in rendered


def test_html_worker_auto_tries_worker_with_fallback():
    rendered = easydot.html("digraph { A -> B }", source="cdn", worker="auto")

    assert 'const workerMode = "auto";' in rendered
    assert "new Worker(url, { type: \"module\" })" in rendered
    assert "Web Worker unavailable; rendering on main thread." in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered
    assert 'showStatus(message, state, false);' in rendered


def test_html_worker_true_requires_worker():
    rendered = easydot.html("digraph { A -> B }", source="cdn", worker=True)

    assert 'const workerMode = "require";' in rendered
    assert "Web Worker rendering was required but failed" in rendered
    assert 'showStatus("Rendering graph...", "info", true);' in rendered


def test_html_worker_false_disables_worker():
    rendered = easydot.html("digraph { A -> B }", source="cdn", worker=False)

    assert 'const workerMode = "disabled";' in rendered
    assert 'showStatus(message, state, false);' in rendered


def test_html_rejects_unknown_worker_value():
    with pytest.raises(ValueError, match="worker must be 'auto', True, or False"):
        easydot.html("digraph { A -> B }", source="cdn", worker="require")


def test_html_fit_true_enables_both_mode():
    rendered = easydot.html("digraph { A -> B }", source="cdn", fit=True, scale=1.5)

    assert 'const fit = "both";' in rendered
    assert "const scale = 1.5;" in rendered
    assert 'class="easydot-fit-both"' in rendered
    assert ".easydot-fit-both > svg" in rendered
    assert "aspect-ratio:var(--easydot-nat-w) / var(--easydot-nat-h)" in rendered
    assert "html,body{margin:0;padding:0;height:100%;overflow:hidden}" in rendered
    assert "svgEl.style.transform" not in rendered


def test_html_fit_horizontal_uses_css_responsiveness():
    rendered = easydot.html("digraph { A -> B }", source="cdn", fit="horizontal", scale=1.5)

    assert 'const fit = "horizontal";' in rendered
    assert 'class="easydot-fit-horizontal"' in rendered
    assert ".easydot-fit-horizontal > svg{width:100%;height:auto;" in rendered
    assert (
        "max-width:calc(var(--easydot-nat-w) * var(--easydot-scale) * 1px)"
        in rendered
    )
    assert "new ResizeObserver(syncFrameHeight).observe(svgEl)" in rendered


def test_html_fit_vertical_uses_flex_viewport():
    rendered = easydot.html("digraph { A -> B }", source="cdn", fit="vertical")

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
        rendered = easydot.html("digraph { A -> B }", source="cdn", fit=fit)
        assert "if (!isViewportFit)" in rendered
        assert "syncFrameHeight" in rendered


def test_html_rejects_unknown_fit_value():
    with pytest.raises(ValueError):
        easydot.html("digraph { A -> B }", source="cdn", fit="diagonal")


def test_html_scale_without_fit_adds_scaled_class_via_js():
    rendered = easydot.html("digraph { A -> B }", source="cdn", scale=2.0)

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
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert "data-easydot-toolbar" in rendered
    assert "data-easydot-copy" in rendered
    assert "data-easydot-download" in rendered
    assert "navigator.clipboard.writeText(svg)" in rendered
    assert "new Blob([svg]" in rendered
    assert "position:sticky" in rendered


def test_html_toolbar_false_omits_toolbar():
    rendered = easydot.html("digraph { A -> B }", source="cdn", toolbar=False)

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
