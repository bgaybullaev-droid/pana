"""
HTML to Markdown Converter for OLX.uz
Converts listing page HTML to clean Markdown for LLM extraction
"""

import json
import re
from typing import Optional, List, Dict, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import markdownify as md, MarkdownConverter
import logging

logger = logging.getLogger(__name__)


class OLXMarkdownConverter(MarkdownConverter):
    """Custom Markdown converter for OLX.uz pages"""

    def convert_img(self, el, text, convert_as_inline):
        """Extract image URLs"""
        src = el.get('src', '')
        alt = el.get('alt', '')
        if src and 'images.olx' in src:
            return f'\n![{alt}]({src})\n'
        return ''

    def convert_a(self, el, text, convert_as_inline):
        """Handle links - keep phone numbers and important links"""
        href = el.get('href', '')
        if href.startswith('tel:'):
            # Phone number
            return f' {text} ({href}) '
        elif 'olx.uz' in href or href.startswith('/'):
            # Internal link - just keep text
            return text
        return text


def extract_main_content(html: str) -> str:
    """
    Remove navigation, ads, footer - keep only main listing content

    Args:
        html: Raw HTML string from Playwright

    Returns:
        Cleaned HTML with only main content
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove unwanted elements
    elements_to_remove = [
        'script', 'style', 'nav', 'footer', 'header',
        'iframe', 'noscript', 'svg', 'form',
        '[data-testid="ad-promotion-button"]',
        '[data-testid="similar-ads"]',
        '[class*="cookie"]',
        '[class*="banner"]',
        '[class*="advertisement"]',
        '[id*="ad-"]',
    ]

    for selector in elements_to_remove:
        for element in soup.select(selector):
            element.decompose()

    # Try to find main content container
    main_content = None

    # OLX-specific content selectors (in order of preference)
    content_selectors = [
        '[data-cy="ad_container"]',
        '[data-testid="ad-detail"]',
        'main',
        '[role="main"]',
        '.ad-details',
        '#ad-container',
    ]

    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    if main_content:
        return str(main_content)

    # If no specific container found, return cleaned body
    body = soup.find('body')
    return str(body) if body else str(soup)


def _extract_location_from_jsonld(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Extract district (and optional city) from JSON-LD schema markup.

    OLX embeds ``<script type="application/ld+json">`` with structure:
        offers.areaServed.name = "Сергелийский район"

    Returns:
        (district, city) — city is None unless the JSON-LD contains it.
    """
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            ld = json.loads(script.string or '')
        except (json.JSONDecodeError, TypeError):
            continue

        # offers may be a dict or a list
        offers = ld.get('offers')
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            continue

        area = offers.get('areaServed')
        if isinstance(area, dict):
            name = area.get('name', '').strip()
            if name:
                return name, None

    return None, None


# Breadcrumb location items use pattern "Продажа - Ташкентская область"
_BREADCRUMB_LOCATION_RE = re.compile(r'^.+\s*-\s*(.+)$')

# Known OLX non-location breadcrumb segments to skip
_SKIP_SEGMENTS = {
    'главная', 'недвижимость', 'квартиры', 'дома', 'земля',
    'коммерческая недвижимость', 'офисы', 'продажа', 'аренда',
    'посуточная аренда', 'долгосрочная аренда',
}


def _extract_location_from_breadcrumbs(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract region, city, district from breadcrumb navigation.

    OLX breadcrumbs look like:
        Главная > Недвижимость > Квартиры > Продажа >
        Продажа - Ташкентская область > Продажа - Ташкент > Продажа - Чиланзарский район

    The last 1–3 items with " - " separator carry location info.

    Strategy: find a ``<ul>`` whose ``<li>`` children contain links to OLX
    category/region paths.  We avoid hard-coding a CSS class name.

    Returns:
        (region, city, district) — any may be None.
    """
    # Heuristic: a breadcrumb list (<ul> or <ol>) has >=5 <li> children,
    # and contains a link to "/" (home page).
    for list_el in soup.find_all(['ul', 'ol']):
        items = list_el.find_all('li', recursive=False)
        if len(items) < 5:
            continue

        # Check that the list contains a link to "/"
        first_link = list_el.select_one('a[href="/"]')
        if not first_link:
            continue

        # This is likely the breadcrumb — extract location segments
        location_parts: List[str] = []
        for li in items:
            text = li.get_text(strip=True)
            m = _BREADCRUMB_LOCATION_RE.match(text)
            if m:
                segment = m.group(1).strip()
                if segment.lower() not in _SKIP_SEGMENTS:
                    location_parts.append(segment)

        # Typical order: [region, city, district]
        region = location_parts[0] if len(location_parts) >= 1 else None
        city = location_parts[1] if len(location_parts) >= 2 else None
        district = location_parts[2] if len(location_parts) >= 3 else None
        return region, city, district

    return None, None, None


def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    """Build a normalized location string from JSON-LD + breadcrumbs.

    Priority:
        1. JSON-LD ``offers.areaServed.name`` for district (most reliable).
        2. Breadcrumbs for region/city/district hierarchy.

    Combines results into a single string: "region, city, district".
    """
    # --- JSON-LD (primary) ---
    jsonld_district, jsonld_city = _extract_location_from_jsonld(soup)

    # --- Breadcrumbs (secondary) ---
    bc_region, bc_city, bc_district = _extract_location_from_breadcrumbs(soup)

    # Merge: prefer JSON-LD district, fall back to breadcrumb district
    district = jsonld_district or bc_district
    city = jsonld_city or bc_city
    region = bc_region  # only available from breadcrumbs

    # Build "region, city, district" — skip duplicates / None
    parts: List[str] = []
    seen_lower: set = set()
    for part in [region, city, district]:
        if part and part.lower() not in seen_lower:
            parts.append(part)
            seen_lower.add(part.lower())

    if parts:
        return ', '.join(parts)

    logger.warning("Location not found in JSON-LD or breadcrumbs")
    return None


def extract_listing_data(html: str) -> Dict[str, str]:
    """
    Extract structured data from OLX listing HTML

    Args:
        html: Raw HTML string

    Returns:
        Dict with extracted fields
    """
    soup = BeautifulSoup(html, 'lxml')
    data = {}

    # Title
    title_el = soup.select_one('h4[data-cy="ad_title"], h1')
    if title_el:
        data['title'] = title_el.get_text(strip=True)

    # Price
    price_el = soup.select_one('[data-testid="ad-price-container"], [class*="price"]')
    if price_el:
        data['price_text'] = price_el.get_text(strip=True)

    # Description
    desc_el = soup.select_one('[data-cy="ad_description"]')
    if desc_el:
        data['description'] = desc_el.get_text(strip=True)

    # Parameters (rooms, area, floor, etc.)
    params_el = soup.select_one('[data-testid="ad-parameters-container"]')
    if params_el:
        data['parameters'] = params_el.get_text(' | ', strip=True)

    # Location — extract from JSON-LD (primary) and breadcrumbs (fallback)
    location = _extract_location(soup)
    if location:
        data['location'] = location

    # Seller info (OLX uses both seller_card and seller-card as data-testid)
    seller_el = soup.select_one('[data-testid="seller_card"], [data-testid="seller-card"]')
    if seller_el:
        data['seller'] = seller_el.get_text(' ', strip=True)
        # Extract seller profile URL
        seller_link = seller_el.select_one('a[href*="/list/user/"], a[href*="/d/user/"], a[href*="/profile/"]')
        if seller_link:
            data['seller_profile_url'] = seller_link.get('href', '')

    # Images - OLX uses apollo.olxcdn.com for image hosting
    images = []
    for img in soup.select('img[src*="apollo.olxcdn.com"]'):
        src = img.get('src', '')
        if src and src not in images:
            # Get full-size image URL (request larger size)
            if ';s=' in src:
                full_src = src.split(';s=')[0] + ';s=1280x960'
            else:
                full_src = src
            images.append(full_src)
    data['images'] = images

    # Posted date
    date_el = soup.select_one('[data-testid="ad-creation-date"]')
    if date_el:
        data['posted_date'] = date_el.get_text(strip=True)

    return data


def convert_html_to_markdown(html: str, include_images: bool = True) -> str:
    """
    Convert OLX listing HTML to clean Markdown

    Args:
        html: Raw HTML string from Playwright
        include_images: Whether to include image URLs

    Returns:
        Clean Markdown string
    """
    # Extract main content first
    content_html = extract_main_content(html)

    # Convert to markdown using custom converter
    markdown = md(
        content_html,
        heading_style='ATX',
        bullets='-',
        strip=['script', 'style', 'nav', 'footer', 'iframe'],
        convert=['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'a', 'img', 'span', 'div'],
    )

    # Clean up the markdown
    markdown = clean_markdown(markdown)

    return markdown


def clean_markdown(markdown: str) -> str:
    """
    Clean and normalize Markdown text

    Args:
        markdown: Raw markdown string

    Returns:
        Cleaned markdown string
    """
    # Remove excessive whitespace
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    # Remove empty links
    markdown = re.sub(r'\[[\s]*\]\([^)]*\)', '', markdown)

    # Remove empty headers
    markdown = re.sub(r'^#+\s*$', '', markdown, flags=re.MULTILINE)

    # Remove lines with only whitespace
    markdown = re.sub(r'^\s+$', '', markdown, flags=re.MULTILINE)

    # Normalize bullet points
    markdown = re.sub(r'^[\*\•]\s+', '- ', markdown, flags=re.MULTILINE)

    # Clean up multiple dashes
    markdown = re.sub(r'-{3,}', '---', markdown)

    # Remove excessive spaces
    markdown = re.sub(r' {2,}', ' ', markdown)

    # Strip leading/trailing whitespace
    markdown = markdown.strip()

    return markdown


def format_listing_markdown(data: Dict[str, str]) -> str:
    """
    Format extracted listing data as clean Markdown

    Args:
        data: Dict with extracted listing fields

    Returns:
        Formatted Markdown string
    """
    lines = []

    # Title
    if data.get('title'):
        lines.append(f"# {data['title']}")
        lines.append('')

    # Price
    if data.get('price_text'):
        lines.append(f"**Цена:** {data['price_text']}")
        lines.append('')

    # Parameters
    if data.get('parameters'):
        lines.append("## Параметры")
        lines.append(data['parameters'].replace(' | ', '\n- '))
        lines.append('')

    # Description
    if data.get('description'):
        lines.append("## Описание")
        lines.append(data['description'])
        lines.append('')

    # Location
    if data.get('location'):
        lines.append(f"**Местоположение:** {data['location']}")
        lines.append('')

    # Seller
    if data.get('seller'):
        lines.append(f"**Продавец:** {data['seller']}")
        lines.append('')

    # Posted date
    if data.get('posted_date'):
        lines.append(f"**Дата:** {data['posted_date']}")
        lines.append('')

    # Images are passed separately to the extractor and stored in JSONB,
    # so we intentionally exclude them from the markdown text to avoid
    # Gemini echoing raw URLs back into the description field.

    return '\n'.join(lines)


def html_to_listing_markdown(html: str) -> tuple[str, Dict]:
    """
    Main entry point: Convert OLX HTML to structured Markdown

    Args:
        html: Raw HTML from Playwright page.content()

    Returns:
        Tuple of (markdown_text, extracted_data_dict)
    """
    # Extract structured data
    data = extract_listing_data(html)

    # Format as clean markdown
    markdown = format_listing_markdown(data)

    # If structured extraction failed, fall back to full conversion
    if not markdown.strip() or len(markdown) < 50:
        logger.warning("Structured extraction yielded minimal content, using full conversion")
        markdown = convert_html_to_markdown(html)

    return markdown, data


# CLI for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        # Read HTML from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html = f.read()

        markdown, data = html_to_listing_markdown(html)

        print("=" * 60)
        print("EXTRACTED DATA:")
        print("=" * 60)
        for key, value in data.items():
            if key == 'images':
                print(f"{key}: {len(value)} images")
            else:
                print(f"{key}: {value[:100]}..." if len(str(value)) > 100 else f"{key}: {value}")

        print("\n" + "=" * 60)
        print("MARKDOWN OUTPUT:")
        print("=" * 60)
        print(markdown)
    else:
        print("Usage: python html_to_markdown.py <html_file>")
