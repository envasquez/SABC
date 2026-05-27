"""Lint-style test enforcing ?v={{ asset_v }} on every app-owned static asset.

Without the cache-bust query string, browsers happily serve stale JS/CSS
after a deploy. We learned this the hard way when a Phase-4 inline-handler
migration looked correct in code but the admin-events page kept firing
the pre-migration JS until a hard refresh — the templates had bare
`<script src="/static/admin-events.js"></script>` tags.

Vendored assets under /static/vendor/ are excluded because they're
versioned by the package itself and rarely change.
"""

import re
from pathlib import Path

import pytest

TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "templates"

# Match: <script src="/static/foo.js"> or <script src="{{ url_for('static', path='/foo.js') }}">
# Tolerates whitespace and additional attributes.
_STATIC_SCRIPT_PATTERN = re.compile(
    r'<script[^>]*\bsrc=(?:"|\')'
    r'(?:/static/|\{\{\s*url_for\([\'"]static[\'"][^}]*path=[\'"]/?)'
    r'([^"\'?]+)',
    re.IGNORECASE,
)

# Match CSS too — same logic applies.
_STATIC_CSS_PATTERN = re.compile(
    r'<link[^>]*\brel=(?:"|\')stylesheet(?:"|\')[^>]*\bhref=(?:"|\')'
    r'(?:/static/|\{\{\s*url_for\([\'"]static[\'"][^}]*path=[\'"]/?)'
    r'([^"\'?]+)',
    re.IGNORECASE,
)


def _iter_template_files() -> list[Path]:
    return [p for p in TEMPLATES_ROOT.rglob("*.html") if p.is_file()]


def _has_cache_bust(line: str) -> bool:
    return "asset_v" in line or "?v=" in line


def _is_vendor(path: str) -> bool:
    # Vendored assets are versioned by the upstream package; the SABC
    # asset_v doesn't apply to them.
    return path.startswith("vendor/")


@pytest.mark.parametrize(
    "template", _iter_template_files(), ids=lambda p: str(p.relative_to(TEMPLATES_ROOT))
)
def test_static_scripts_have_cache_bust(template: Path) -> None:
    """Every <script src="/static/..."> in a template must carry ?v={{ asset_v }}.

    Cached browsers were serving pre-migration JS after Phase 4 because
    several admin templates loaded their bundles without cache-bust.
    Locks the convention in so it can't regress silently.
    """
    text = template.read_text()
    offenders: list[tuple[int, str, str]] = []
    for match in _STATIC_SCRIPT_PATTERN.finditer(text):
        path = match.group(1)
        if _is_vendor(path):
            continue
        # Locate the line for a useful error message
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        if not _has_cache_bust(line):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append((line_no, path, line.strip()))

    assert not offenders, (
        f"{template.relative_to(TEMPLATES_ROOT)}: static script tag(s) missing "
        f"`?v={{{{ asset_v }}}}` cache-bust:\n"
        + "\n".join(f"  L{ln}  /static/{p}\n    {line}" for ln, p, line in offenders)
    )


@pytest.mark.parametrize(
    "template", _iter_template_files(), ids=lambda p: str(p.relative_to(TEMPLATES_ROOT))
)
def test_static_stylesheets_have_cache_bust(template: Path) -> None:
    """Same rule as scripts, applied to CSS link tags."""
    text = template.read_text()
    offenders: list[tuple[int, str, str]] = []
    for match in _STATIC_CSS_PATTERN.finditer(text):
        path = match.group(1)
        if _is_vendor(path):
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        if not _has_cache_bust(line):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append((line_no, path, line.strip()))

    assert not offenders, (
        f"{template.relative_to(TEMPLATES_ROOT)}: static stylesheet(s) missing "
        f"`?v={{{{ asset_v }}}}` cache-bust:\n"
        + "\n".join(f"  L{ln}  /static/{p}\n    {line}" for ln, p, line in offenders)
    )
