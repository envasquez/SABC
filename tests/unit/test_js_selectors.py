"""Lint-style test: every class a JS file selects on must exist somewhere.

The Tabler UI rebuild renamed the calendar's event-day cells from
`.cal-event-day` to `.ev`, but `calendar.js` kept calling
`closest('.cal-event-day')`. Nothing threw — `closest()` just returns
null — so clicking a highlighted day silently did nothing for months.
The same rename orphaned `closest('.fg')` in admin-events-forms.js.

Silent-null selectors are invisible to the other test layers (route
tests render HTML, they don't run JS), so this scans the JS for class
selectors and fails when one matches nothing in the templates, the
project CSS, the vendored Tabler CSS, or a class the JS itself creates.
"""

import re
from pathlib import Path
from typing import Set

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"

# Stylesheets a selector may legitimately be defined by.
CSS_FILES = [
    STATIC / "sabc.css",
    STATIC / "enter-results.css",
    STATIC / "vendor" / "tabler" / "tabler.min.css",
]

# .querySelector('…') / .querySelectorAll('…') / .closest('…') / .matches('…')
_SELECTOR_CALL = re.compile(
    r"""\.(?:querySelector|querySelectorAll|closest|matches)\(\s*(['"`])(.*?)\1""",
    re.DOTALL,
)

# Class tokens inside a selector string: `.foo`, `td.ev`, `.a > .b`.
_CLASS_TOKEN = re.compile(r"\.(-?[A-Za-z_][\w-]*)")

# `class="a b c"` written inside a JS string (JS-built markup).
_JS_CLASS_ATTR = re.compile(r"""class=\\?["']([^"'<>\\]+)""")

# classList.add('x') / .remove('x') / .toggle('x') / .contains('x')
_CLASS_LIST = re.compile(r"""classList\.(?:add|remove|toggle|contains)\(\s*['"]([\w-]+)""")

# `class="a b"` / `class='a b'` in a Jinja template. Kept as two alternatives
# so an inner quote (`class="{% if '\u2020' in d %}ev{% endif %}"`) doesn't truncate.
_TEMPLATE_CLASS_ATTR = re.compile(r"""class="([^"]*)"|class='([^']*)'""")


def _js_files() -> list[Path]:
    return sorted(p for p in STATIC.glob("*.js") if p.is_file())


def _known_classes() -> Set[str]:
    """Every class name the app could plausibly render."""
    known: Set[str] = set()

    # Classes written into templates, including inside {% if %} branches.
    for template in TEMPLATES.rglob("*.html"):
        for double, single in _TEMPLATE_CLASS_ATTR.findall(template.read_text()):
            # Strip Jinja expressions, keep the literal class tokens from every
            # branch of a conditional attribute.
            known.update(re.sub(r"\{[{%].*?[%}]\}", " ", double or single, flags=re.DOTALL).split())

    # Classes defined by a stylesheet we ship or vendor.
    for css in CSS_FILES:
        known.update(re.findall(r"\.(-?[A-Za-z_][\w-]*)", css.read_text()))

    # Classes the JS itself puts on elements.
    for js in _js_files():
        text = js.read_text()
        known.update(_CLASS_LIST.findall(text))
        for attr in _JS_CLASS_ATTR.findall(text):
            known.update(attr.split())

    return known


KNOWN_CLASSES = _known_classes()


@pytest.mark.parametrize("js_file", _js_files(), ids=lambda p: p.name)
def test_js_class_selectors_exist(js_file: Path) -> None:
    """A class selector that matches nothing is a silently dead handler."""
    text = js_file.read_text()
    orphans: list[tuple[int, str, str]] = []

    for match in _SELECTOR_CALL.finditer(text):
        selector = match.group(2)
        # Template literals build selectors at runtime; nothing to check.
        if "${" in selector:
            continue
        for class_name in _CLASS_TOKEN.findall(selector):
            if class_name not in KNOWN_CLASSES:
                line_no = text.count("\n", 0, match.start()) + 1
                orphans.append((line_no, selector, class_name))

    assert not orphans, (
        f"{js_file.name}: selector(s) referencing a class that exists in no "
        f"template, stylesheet, or JS-generated markup — these match nothing "
        f"at runtime and fail silently:\n"
        + "\n".join(f"  L{ln}  '{sel}'  (unknown class .{cls})" for ln, sel, cls in orphans)
    )
