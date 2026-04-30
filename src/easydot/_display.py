"""Shared display primitives for static SVG rendering across all backends."""

from __future__ import annotations

import base64
import html as html_lib
import json
import re
import uuid

from easydot._icons import CHECK_ICON, COPY_ICON, DOWNLOAD_ICON


_FIT_MODES = ("none", "horizontal", "vertical", "both")


def normalize_fit(value: bool | str) -> str:
    if isinstance(value, bool):
        return "both" if value else "none"
    if isinstance(value, str) and value in _FIT_MODES:
        return value
    raise ValueError(
        "fit must be True, False, or one of 'horizontal', 'vertical', 'both', 'none'; "
        f"got {value!r}"
    )


_VIEWBOX_RE = re.compile(r'<svg\b[^>]*\bviewBox="([^"]+)"', re.IGNORECASE)
_WH_RE = re.compile(r'<svg\b[^>]*\bwidth="([^"]+)"[^>]*\bheight="([^"]+)"', re.IGNORECASE)
_PT_SCALE = 4 / 3  # 1pt = 1.333... px


def _parse_length(value: str) -> float:
    """Parse a CSS length string to float pixels."""
    value = value.strip()
    if value.endswith("pt"):
        return float(value[:-2]) * _PT_SCALE
    if value.endswith("px"):
        return float(value[:-2])
    if value.endswith("in"):
        return float(value[:-2]) * 96
    if value.endswith("cm"):
        return float(value[:-2]) * 37.795
    if value.endswith("mm"):
        return float(value[:-2]) * 3.7795
    return float(value)


def extract_natural_size(svg: str) -> tuple[float, float]:
    """Return natural SVG dimensions in CSS pixels.

    Explicit width/height attributes are preferred because browser SVG layout
    resolves those lengths before applying fit CSS. Falls back to viewBox width
    and height when explicit dimensions are absent.
    """
    m = _WH_RE.search(svg)
    if m:
        return _parse_length(m.group(1)), _parse_length(m.group(2))
    m = _VIEWBOX_RE.search(svg)
    if m:
        parts = m.group(1).split()
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])
    return 100.0, 100.0


def extract_viewbox(svg: str) -> tuple[float, float]:
    """Return natural SVG dimensions.

    Kept for internal compatibility; use :func:`extract_natural_size` for new
    code.
    """
    return extract_natural_size(svg)


_PROLOG_RE = re.compile(
    r'^(\s*<\?xml[^?]*\?>\s*)?(\s*<!DOCTYPE[^>]*>\s*)?(\s*<!--.*?-->\s*)*',
    re.DOTALL,
)
_SVG_WH_RE = re.compile(
    r'(<svg\b[^>]*?)\s+width="[^"]*"\s+height="[^"]*"',
    re.IGNORECASE | re.DOTALL,
)
_SVG_WH_REVERSED_RE = re.compile(
    r'(<svg\b[^>]*?)\s+height="[^"]*"\s+width="[^"]*"',
    re.IGNORECASE | re.DOTALL,
)


def inline_svg(svg: str) -> str:
    """Prepare an SVG string for inline HTML embedding.

    - Strips XML prolog, DOCTYPE declaration, and leading comments.
    - Replaces width/height attributes with width="100%" height="100%"
      so that CSS controls sizing via viewBox + aspect-ratio.
    - Preserves viewBox and all other attributes.
    """
    svg = _PROLOG_RE.sub("", svg).strip()
    # Replace width+height (either order)
    svg = _SVG_WH_RE.sub(r'\1 width="100%" height="100%"', svg)
    svg = _SVG_WH_REVERSED_RE.sub(r'\1 width="100%" height="100%"', svg)
    return svg


def layout_stylesheet(attr_id: str) -> str:
    """CSS that implements the two-axis fit model.

    Width axis: natural*scale (default) or fit-container (horizontal, both).
    Height axis: natural*scale (default) or fit-viewport (vertical, both).
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


def body_stylesheet(fit: str) -> str:
    if fit in ("vertical", "both"):
        return "html,body{margin:0;padding:0;height:100%;overflow:hidden}"
    return "html,body{margin:0;padding:0}"


def fit_lifecycle_script() -> str:
    return r"""
const setupEasydotFit = (target, fit, scale, observe = true) => {
  const syncFrameHeight = () => {
    const frame = window.frameElement;
    if (!frame) return;
    try {
      frame.style.height = `${Math.ceil(target.scrollHeight)}px`;
    } catch (_err) {
      /* cross-origin frames reject the write; best-effort only */
    }
  };
  const readCssNumber = (name) => {
    const value = getComputedStyle(target).getPropertyValue(name).trim();
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : null;
  };
  const svgEl = target.querySelector(":scope > svg");
  if (svgEl && (readCssNumber("--easydot-nat-w") === null || readCssNumber("--easydot-nat-h") === null)) {
    const vb = svgEl.viewBox && svgEl.viewBox.baseVal;
    const width = svgEl.width && svgEl.width.baseVal;
    const height = svgEl.height && svgEl.height.baseVal;
    const rect = svgEl.getBoundingClientRect();
    const naturalW = (width && width.value) || (vb && vb.width) || rect.width || 1;
    const naturalH = (height && height.value) || (vb && vb.height) || rect.height || 1;
    target.style.setProperty("--easydot-nat-w", String(naturalW));
    target.style.setProperty("--easydot-nat-h", String(naturalH));
  }
  target.style.setProperty("--easydot-scale", String(scale));
  if (fit === "none" && scale !== 1) {
    target.classList.add("easydot-scaled");
  }

  const isViewportFit = fit === "vertical" || fit === "both";
  if (observe && !isViewportFit) {
    const scheduleFrameHeightSync = () => requestAnimationFrame(syncFrameHeight);
    scheduleFrameHeightSync();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(scheduleFrameHeightSync);
      observer.observe(target);
      if (svgEl) {
        observer.observe(svgEl);
      }
    }
    window.addEventListener("resize", scheduleFrameHeightSync);
  }
  return { syncFrameHeight };
};
"""


def toolbar_stylesheet(attr_id: str) -> str:
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


def static_toolbar_html(attr_id: str, svg_text: str) -> str:
    """Toolbar markup with copy/download buttons for static (non-browser) backends."""
    svg_b64 = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    check_icon_json = repr(CHECK_ICON).replace("'", '"')
    return (
        f'<div class="easydot-toolbar" data-easydot-toolbar data-svg="{svg_b64}">'
        f'<button type="button" data-easydot-copy aria-label="Copy SVG to clipboard" title="Copy SVG">{COPY_ICON}</button>'
        f'<button type="button" data-easydot-download aria-label="Download SVG" title="Download SVG">{DOWNLOAD_ICON}</button>'
        "</div>"
        "<script>"
        "(function(){"
        f'var tb=document.currentScript.previousElementSibling;'
        "if(!tb)return;"
        "var svgB64=tb.dataset.svg;"
        "var svgText=typeof atob!=='undefined'?decodeURIComponent(escape(atob(svgB64))):Buffer.from(svgB64,'base64').toString();"
        f"var checkIcon={check_icon_json};"
        "function flash(btn,ok){"
        "var orig=btn.dataset.orig||(btn.dataset.orig=btn.innerHTML);"
        "btn.classList.remove('is-success','is-error');"
        "btn.classList.add(ok?'is-success':'is-error');"
        "if(ok)btn.innerHTML=checkIcon;"
        "clearTimeout(btn._t);"
        "btn._t=setTimeout(function(){btn.innerHTML=orig;btn.classList.remove('is-success','is-error');},1100);"
        "}"
        "var copy=tb.querySelector('[data-easydot-copy]');"
        "var dl=tb.querySelector('[data-easydot-download]');"
        "if(copy)copy.addEventListener('click',function(){"
        "if(navigator.clipboard){navigator.clipboard.writeText(svgText).then(function(){flash(copy,true);},function(){flash(copy,false);});}else{flash(copy,false);}"
        "});"
        "if(dl)dl.addEventListener('click',function(){"
        "try{"
        "var blob=new Blob([svgText],{type:'image/svg+xml;charset=utf-8'});"
        "var url=URL.createObjectURL(blob);"
        "var a=document.createElement('a');a.href=url;a.download='graph.svg';"
        "document.body.appendChild(a);a.click();a.remove();"
        "setTimeout(function(){URL.revokeObjectURL(url);},0);"
        "flash(dl,true);"
        "}catch(e){flash(dl,false);}"
        "});"
        "})()"
        "</script>"
    )


def wrap_static_html(
    svg: str,
    *,
    fit: str,
    scale: float,
    toolbar: bool,
    container_id: str | None = None,
) -> str:
    """Wrap a static SVG in the standard easydot display wrapper.

    Sets --easydot-nat-w/--easydot-nat-h from the SVG at render time and runs
    the shared fit lifecycle used by the browser backend.
    """
    if container_id is None:
        container_id = f"easydot-{uuid.uuid4().hex}"

    attr_id = html_lib.escape(container_id, quote=True)
    nat_w, nat_h = extract_natural_size(svg)
    inlined = inline_svg(svg)

    style_attr = (
        f"--easydot-nat-w:{nat_w:.4f};"
        f"--easydot-nat-h:{nat_h:.4f};"
        f"--easydot-scale:{float(scale):.4f}"
    )
    if scale != 1.0:
        fit_class = f"easydot-fit-{fit} easydot-scaled"
    else:
        fit_class = f"easydot-fit-{fit}"

    layout_style = body_stylesheet(fit) + layout_stylesheet(attr_id)
    toolbar_html = ""
    if toolbar:
        toolbar_html = static_toolbar_html(attr_id, svg)
        layout_style += toolbar_stylesheet(attr_id)

    fit_script = (
        "<script>"
        f"{fit_lifecycle_script()}"
        f"setupEasydotFit(document.getElementById({json.dumps(container_id)}), {json.dumps(fit)}, {json.dumps(float(scale))});"
        "</script>"
    )

    return (
        f'<style>{layout_style}</style>'
        f'<div id="{attr_id}" class="{fit_class}" style="{style_attr}">'
        f'{toolbar_html}'
        f'{inlined}'
        f'</div>'
        f'{fit_script}'
    )
