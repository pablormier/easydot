from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from urllib.request import urlopen

import pytest

import easydot
from easydot._html import DEFAULT_CDN_URL


def _install_fake_marimo(monkeypatch, iframe_impl):
    marimo_module = ModuleType("marimo")
    output_module = ModuleType("marimo._output")
    formatting_module = ModuleType("marimo._output.formatting")
    formatting_module.iframe = iframe_impl

    monkeypatch.setitem(sys.modules, "marimo", marimo_module)
    monkeypatch.setitem(sys.modules, "marimo._output", output_module)
    monkeypatch.setitem(sys.modules, "marimo._output.formatting", formatting_module)


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


def test_html_auto_includes_cdn_fallback_after_local_url():
    rendered = easydot.html("digraph { A -> B }")

    assert "http://127.0.0.1:" in rendered
    assert DEFAULT_CDN_URL in rendered
    assert "for (const url of moduleUrls)" in rendered


def test_html_cdn_source_avoids_local_url():
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert DEFAULT_CDN_URL in rendered
    assert "http://127.0.0.1:" not in rendered


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
    assert "digraph { A -> B }" not in html


def test_html_defaults_omit_fit_and_scale():
    rendered = easydot.html("digraph { A -> B }", source="cdn")

    assert "const fit = false;" in rendered
    assert "const scale = 1.0;" in rendered


def test_html_fit_and_scale_flags_are_embedded():
    rendered = easydot.html("digraph { A -> B }", source="cdn", fit=True, scale=1.5)

    assert "const fit = true;" in rendered
    assert "const scale = 1.5;" in rendered
    assert 'svgEl.style.maxWidth = "100%"' in rendered
    assert "svgEl.style.transform = `scale(${scale})`" in rendered


@pytest.mark.skipif(
    importlib.util.find_spec("marimo") is None,
    reason="marimo not installed",
)
def test_display_mime_integrates_with_real_marimo():
    mime, payload = easydot.display(
        "digraph { A -> B }",
        source="cdn",
        fit=True,
        scale=1.25,
    )._mime_()

    assert mime == "text/html"
    assert "<iframe" in payload
    assert "srcdoc" in payload
    assert "Graphviz.load" in payload


def test_display_mime_uses_marimo_iframe(monkeypatch):
    expected = '<iframe srcdoc="<p>ok</p>"></iframe>'

    class _Frame:
        def _mime_(self):
            return "text/html", expected

    _install_fake_marimo(monkeypatch, lambda *_args, **_kwargs: _Frame())

    mime, payload = easydot.display("digraph { A -> B }", source="cdn")._mime_()

    assert mime == "text/html"
    assert payload == expected
