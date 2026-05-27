"""Lint-style test: forbid Jinja block definitions nested inside admin_content/content.

We learned this the hard way in May 2026: events.html (and 5 other admin
templates) had `{% block extra_js %}...{% endblock %}` defined INSIDE
`{% block admin_content %}`. Jinja renders nested block definitions twice —
once inline where they appear in the parent block, once at the base-template
extension point. The result was every admin-events*.js loaded twice, which
registered the click delegated listener twice, which fired `editEvent` twice
per click, which opened the modal twice (two backdrops). Closing the modal
removed only the topmost backdrop; the leftover backdrop intercepted every
subsequent click, effectively freezing the page.

This guard fails CI if any template defines a sub-block inside admin_content
or content. Sibling blocks (`{% endblock %}{% block extra_js %}{% endblock %}`)
are fine — Jinja renders them once at the extension point as intended.
"""

import re
from pathlib import Path

import pytest

TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "templates"

# Blocks that base.html renders at extension points DISTINCT from the body
# (`{% block content %}`). If a child template defines one of these *inside*
# another block, Jinja will render it twice — once inline in the parent
# block, once at the dedicated extension point in base.html. The actual
# footgun is `extra_js` / `extra_css` (rendered near `</head>` and `</body>`
# respectively, independent of content position). `admin_content` is safe
# to nest inside `content` because admin_base.html owns the only extension
# point for it.
_DOUBLE_RENDER_BLOCKS = {"extra_js", "extra_css"}

_BLOCK_TAG = re.compile(r"\{%\s*(block\s+\w+|endblock(?:\s+\w+)?)\s*%\}")


def _iter_template_files() -> list[Path]:
    return [p for p in TEMPLATES_ROOT.rglob("*.html") if p.is_file()]


def _find_nested_blocks(text: str) -> list[tuple[str, str, int]]:
    """Return (parent_block, nested_block_name, line_no) for any extra_js/extra_css
    defined inside another block — that pattern double-renders."""
    offenders: list[tuple[str, str, int]] = []
    stack: list[str] = []  # currently-open block names

    for tok in _BLOCK_TAG.finditer(text):
        raw = tok.group(1)
        parts = raw.split()
        if parts[0] == "block":
            name = parts[1]
            if stack and name in _DOUBLE_RENDER_BLOCKS:
                line_no = text.count("\n", 0, tok.start()) + 1
                offenders.append((stack[-1], name, line_no))
            stack.append(name)
        else:  # endblock
            if stack:
                stack.pop()
    return offenders


@pytest.mark.parametrize(
    "template", _iter_template_files(), ids=lambda p: str(p.relative_to(TEMPLATES_ROOT))
)
def test_extra_js_and_extra_css_blocks_are_not_nested(template: Path) -> None:
    """`{% block extra_js %}` and `{% block extra_css %}` must be sibling blocks,
    not nested inside another block.

    These two blocks have dedicated extension points in base.html (in <head>
    and before </body>) that are rendered independently of `{% block content %}`.
    If a child template defines them inside another block, Jinja renders them
    twice — once inline in the parent, once at the dedicated extension point.

    The May 2026 modal-freeze bug on /admin/events was caused exactly by this:
    extra_js nested inside admin_content loaded every admin-events*.js twice,
    which registered the click delegated listener twice, which fired editEvent
    twice per click, which opened the modal twice (two backdrops). Closing
    the modal removed only the topmost backdrop — the leftover intercepted
    every subsequent click and froze the page.
    """
    text = template.read_text()
    offenders = _find_nested_blocks(text)
    assert not offenders, (
        f"{template.relative_to(TEMPLATES_ROOT)}: blocks defined inside "
        f"a parent extension-point block (will render twice):\n"
        + "\n".join(
            f"  L{ln}: {{% block {nested} %}} nested inside {{% block {parent} %}}"
            for parent, nested, ln in offenders
        )
    )
