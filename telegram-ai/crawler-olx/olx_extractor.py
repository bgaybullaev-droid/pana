"""
OLX Extractor - Wrapper around LLM Extractor for OLX.uz
Adapts the existing Telegram-focused extractor for web content
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional, Any

# Add parent crawler directory to path for imports
CRAWLER_DIR = Path(__file__).parent.parent / "crawler"
sys.path.insert(0, str(CRAWLER_DIR))

from llm_extractor import LLMExtractor
from schema_loader import SchemaLoader

logger = logging.getLogger(__name__)


class OLXExtractor:
    """
    Wrapper for LLM-based data extraction from OLX listings

    Adapts the existing LLMExtractor (designed for Telegram) to work with
    Markdown content converted from OLX HTML pages.
    """

    def __init__(self, schema_name: str = "real_estate", provider: str = None):
        """
        Initialize the OLX extractor

        Args:
            schema_name: Name of schema to use (default: real_estate)
            provider: LLM provider override ('anthropic', 'openai', 'gemini')
        """
        # Initialize the LLM extractor
        self.llm = LLMExtractor(provider=provider)

        # Load schema from parent crawler's schemas directory
        self.schema_loader = SchemaLoader(schemas_dir=str(CRAWLER_DIR / "schemas"))

        # Access schema directly from schemas dict
        self.schema = self.schema_loader.schemas.get(schema_name)

        if not self.schema:
            # Try to load from local schemas directory
            local_schemas = Path(__file__).parent / "schemas"
            local_loader = SchemaLoader(schemas_dir=str(local_schemas))
            self.schema = local_loader.schemas.get(schema_name)

        if not self.schema:
            available = self.schema_loader.list_schemas()
            raise ValueError(f"Schema '{schema_name}' not found. Available: {available}")

        logger.info(f"✅ OLX Extractor initialized with schema: {schema_name}")

    def preprocess_olx_content(self, markdown: str) -> str:
        """
        Pre-process OLX markdown content before LLM extraction

        Args:
            markdown: Markdown text converted from HTML

        Returns:
            Cleaned markdown ready for extraction
        """
        # Remove excessive whitespace
        lines = markdown.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)

        markdown = '\n'.join(cleaned_lines)

        # Remove image markdown (keep URLs in separate field)
        import re
        markdown = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', markdown)

        # Remove excessive dashes/separators
        markdown = re.sub(r'-{3,}', '', markdown)
        markdown = re.sub(r'={3,}', '', markdown)

        # Clean up empty headers
        markdown = re.sub(r'^#+\s*$', '', markdown, flags=re.MULTILINE)

        # Remove navigation remnants
        nav_patterns = [
            r'Главная.*?(?=\n)',
            r'Недвижимость.*?(?=\n)',
            r'Breadcrumb.*?(?=\n)',
            r'← Назад',
            r'Поделиться',
        ]
        for pattern in nav_patterns:
            markdown = re.sub(pattern, '', markdown, flags=re.IGNORECASE)

        return markdown.strip()

    def extract_from_markdown(self, markdown: str, listing_id: Optional[str] = None) -> Optional[Dict]:
        """
        Extract structured data from OLX listing markdown

        Args:
            markdown: Markdown text from HTML conversion
            listing_id: OLX listing ID (from URL)

        Returns:
            Dict with extracted fields or None if extraction failed
        """
        # Preprocess the content
        cleaned_markdown = self.preprocess_olx_content(markdown)

        if len(cleaned_markdown) < 30:
            logger.warning(f"Content too short for extraction: {len(cleaned_markdown)} chars")
            return None

        # Use the LLM extractor with 'olx_uz' as the source identifier
        result = self.llm.extract(
            schema=self.schema,
            message_text=cleaned_markdown,
            retry=True,
            skip_prefilter=True,  # Skip Telegram-specific pre-filtering
            channel="olx_uz"  # Identifier for caching and few-shot selection
        )

        if result:
            # Add OLX-specific metadata
            result['source'] = 'olx_uz'
            if listing_id:
                result['olx_id'] = listing_id

        return result

    def postprocess_extraction(self, data: Dict) -> Dict:
        """
        Post-process extracted data for consistency

        Args:
            data: Raw extracted data from LLM

        Returns:
            Normalized data dict
        """
        if not data:
            return {}

        # Normalize currency
        if 'currency' in data:
            currency = str(data['currency']).upper()
            if currency in ['$', 'USD', 'У.Е.', 'У.Е', 'DOLLAR', 'ДОЛЛАР']:
                data['currency'] = 'USD'
            elif currency in ['СУМ', "SO'M", 'SUM', 'UZS']:
                data['currency'] = 'UZS'

        # Normalize property type
        if 'property_type' in data:
            prop_type = str(data['property_type']).lower()
            type_mapping = {
                'квартира': 'apartment',
                'apartment': 'apartment',
                'kvartira': 'apartment',
                'дом': 'house',
                'house': 'house',
                'uy': 'house',
                'земля': 'land',
                'land': 'land',
                'yer': 'land',
                'участок': 'land',
                'коммерческая': 'commercial',
                'commercial': 'commercial',
                'офис': 'commercial',
                'office': 'commercial',
            }
            data['property_type'] = type_mapping.get(prop_type, prop_type)

        # Normalize listing type
        if 'listing_type' in data:
            listing_type = str(data['listing_type']).lower()
            type_mapping = {
                'продажа': 'sell',
                'sale': 'sell',
                'sell': 'sell',
                'sotiladi': 'sell',
                'продается': 'sell',
                'аренда': 'rent',
                'rent': 'rent',
                'ijaraga': 'rent',
                'посуточно': 'rent',
                'daily_rent': 'rent',
                'sutkalik': 'rent',
            }
            data['listing_type'] = type_mapping.get(listing_type, listing_type)

        # Ensure numeric fields are numbers
        numeric_fields = ['price', 'rooms', 'area_sqm', 'floor', 'total_floors']
        for field in numeric_fields:
            if field in data and data[field] is not None:
                try:
                    value = str(data[field]).replace(',', '.').replace(' ', '')
                    data[field] = float(value) if '.' in value else int(value)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert {field}={data[field]} to number")
                    data[field] = None

        return data

    def extract(self, markdown: str, listing_id: Optional[str] = None,
                images: Optional[list] = None) -> Optional[Dict]:
        """
        Main extraction method - complete pipeline

        Args:
            markdown: Markdown text from OLX listing
            listing_id: OLX listing ID
            images: List of image URLs

        Returns:
            Complete extracted and normalized data
        """
        # Extract raw data
        raw_data = self.extract_from_markdown(markdown, listing_id)

        if not raw_data:
            return None

        # Post-process
        data = self.postprocess_extraction(raw_data)

        # Add images if provided
        if images:
            data['images'] = images

        return data


# CLI for testing
if __name__ == '__main__':
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test extraction
    test_markdown = """
    # 3-комнатная квартира, Юнусабад

    **Цена:** 85 000 у.е.

    ## Параметры
    - Количество комнат: 3
    - Общая площадь: 80 м²
    - Этаж: 4 / 9
    - Ремонт: евроремонт

    ## Описание
    Продается 3-комнатная квартира в районе Юнусабад.
    Квартира с хорошим ремонтом, мебелью и техникой.
    Рядом метро, школа, детский сад.

    **Контакт:** +998 90 123 45 67
    """

    print("=" * 60)
    print("Testing OLX Extractor")
    print("=" * 60)

    try:
        extractor = OLXExtractor()
        result = extractor.extract(test_markdown, listing_id="TEST123")

        if result:
            print("\n✅ Extraction successful:")
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\n❌ Extraction failed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
