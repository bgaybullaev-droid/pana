"""Tests for OLX location extraction (JSON-LD + breadcrumbs)."""
import sys
from pathlib import Path

# Add parent dir so we can import html_to_markdown
sys.path.insert(0, str(Path(__file__).parent.parent))

from html_to_markdown import (
    _extract_location_from_jsonld,
    _extract_location_from_breadcrumbs,
    _extract_location,
    extract_listing_data,
    format_listing_markdown,
)
from bs4 import BeautifulSoup

FIXTURES = Path(__file__).parent / "fixtures"


def _soup(filename: str) -> BeautifulSoup:
    html = (FIXTURES / filename).read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


# ── JSON-LD extraction ──────────────────────────────────────────────

def test_jsonld_extracts_district():
    soup = _soup("listing_with_jsonld.html")
    district, city = _extract_location_from_jsonld(soup)
    assert district == "Чиланзарский район", f"Expected Чиланзарский район, got {district!r}"
    assert city is None


def test_jsonld_returns_none_when_missing():
    soup = _soup("listing_breadcrumbs_only.html")
    district, city = _extract_location_from_jsonld(soup)
    assert district is None
    assert city is None


def test_jsonld_returns_none_for_no_area():
    soup = _soup("listing_no_location.html")
    district, city = _extract_location_from_jsonld(soup)
    assert district is None


# ── Breadcrumb extraction ───────────────────────────────────────────

def test_breadcrumbs_extract_full_hierarchy():
    soup = _soup("listing_with_jsonld.html")
    region, city, district = _extract_location_from_breadcrumbs(soup)
    assert region == "Ташкентская область", f"region: {region!r}"
    assert city == "Ташкент", f"city: {city!r}"
    assert district == "Чиланзарский район", f"district: {district!r}"


def test_breadcrumbs_work_with_different_css_class():
    """Breadcrumb <ul> has class css-abc123, not css-xv75xi — must still work."""
    soup = _soup("listing_breadcrumbs_only.html")
    region, city, district = _extract_location_from_breadcrumbs(soup)
    assert region == "Ташкентская область"
    assert city == "Ташкент"
    assert district == "Сергелийский район"


def test_breadcrumbs_return_none_when_missing():
    soup = _soup("listing_no_location.html")
    region, city, district = _extract_location_from_breadcrumbs(soup)
    assert region is None
    assert city is None
    assert district is None


# ── Combined _extract_location ──────────────────────────────────────

def test_combined_jsonld_plus_breadcrumbs():
    soup = _soup("listing_with_jsonld.html")
    loc = _extract_location(soup)
    # Should contain region, city, district (deduped with JSON-LD)
    assert "Ташкентская область" in loc
    assert "Ташкент" in loc
    assert "Чиланзарский район" in loc


def test_combined_breadcrumbs_only():
    soup = _soup("listing_breadcrumbs_only.html")
    loc = _extract_location(soup)
    assert "Сергелийский район" in loc
    assert "Ташкент" in loc


def test_combined_returns_none_for_no_location():
    soup = _soup("listing_no_location.html")
    loc = _extract_location(soup)
    assert loc is None


# ── Full pipeline: extract_listing_data → format_listing_markdown ───

def test_markdown_contains_location_line():
    html = (FIXTURES / "listing_with_jsonld.html").read_text(encoding="utf-8")
    data = extract_listing_data(html)
    md = format_listing_markdown(data)
    assert "**Местоположение / Location:**" in md
    assert "Чиланзарский район" in md


def test_markdown_contains_location_from_breadcrumbs():
    html = (FIXTURES / "listing_breadcrumbs_only.html").read_text(encoding="utf-8")
    data = extract_listing_data(html)
    md = format_listing_markdown(data)
    assert "**Местоположение / Location:**" in md
    assert "Сергелийский район" in md


def test_markdown_no_location_when_missing():
    html = (FIXTURES / "listing_no_location.html").read_text(encoding="utf-8")
    data = extract_listing_data(html)
    md = format_listing_markdown(data)
    assert "Местоположение" not in md


# ── Runner ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed else 0)
