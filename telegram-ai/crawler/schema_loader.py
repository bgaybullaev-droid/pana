"""
Schema Loader and Manager
=========================

Field-extraction schemas are still loaded from YAML files (extraction
patterns, field types, validation rules — code-shaped configuration).

The **channel list** itself, per Block A V2.0 (A8), comes from the
``parser_sources`` table in Postgres. The legacy YAML ``channels:`` key
is still read as a fallback when the DB is unreachable, but it is
otherwise ignored.

Refresh model: ``SchemaLoader`` snapshots the channel list at construct
time. Long-running crawler processes should call
``loader.refresh_channels_from_db()`` periodically (e.g. every 10 min)
to pick up admin-side pause/resume/add/delete events without restart.
"""

import os
import yaml
import re
from typing import Dict, List, Optional, Any
from datetime import datetime


# Resolve the default schema name for a given source type. Today there
# is one schema (``real_estate``); when more land, this map gates the
# routing without needing a schema_name column on parser_sources.
_DEFAULT_SCHEMA_BY_TYPE = {
    "telegram_channel": "real_estate",
    "olx": "real_estate",
    "website": "real_estate",
    "other": "real_estate",
}


class SchemaLoader:
    """Load and manage channel schemas.

    Channel→schema mapping comes from Postgres (``parser_sources``);
    the field schemas themselves are still loaded from YAML.
    """

    def __init__(self, schemas_dir='schemas', use_db_sources: bool = True):
        self.schemas_dir = schemas_dir
        self.schemas: Dict[str, Dict] = {}
        self.channel_to_schema: Dict[str, str] = {}
        self._use_db_sources = use_db_sources
        self.load_all_schemas()
        if use_db_sources:
            self.refresh_channels_from_db()

    def load_all_schemas(self):
        """Load all YAML schema files from schemas directory.

        This intentionally does NOT populate ``channel_to_schema``
        anymore — channels come from the DB via
        :meth:`refresh_channels_from_db`. The YAML ``channels:`` key
        is treated as a fallback when DB is unreachable.
        """
        if not os.path.exists(self.schemas_dir):
            print(f"Warning: Schemas directory '{self.schemas_dir}' not found")
            return

        for filename in os.listdir(self.schemas_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                schema_path = os.path.join(self.schemas_dir, filename)
                try:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = yaml.safe_load(f)

                    schema_name = schema.get('schema_name')
                    if not schema_name:
                        print(f"Warning: Schema in {filename} missing 'schema_name', skipping")
                        continue

                    self.schemas[schema_name] = schema
                    yaml_channels = schema.get('channels', []) or []
                    print(
                        f"Loaded schema '{schema_name}' "
                        f"(YAML lists {len(yaml_channels)} legacy channels — DB is the source of truth)"
                    )

                except Exception as e:
                    print(f"Error loading schema {filename}: {e}")

    # ── DB-driven channel list ────────────────────────────────────────

    def refresh_channels_from_db(self) -> int:
        """Reload the active channel list from ``parser_sources``.

        Returns the number of telegram channels loaded. On DB error,
        falls back to the YAML ``channels:`` lists from the loaded
        schemas so the crawler keeps working in degraded mode.
        """
        try:
            from .db_sources import load_active_sources  # type: ignore
        except ImportError:
            # Local-script execution (no package context) — try absolute import.
            try:
                from db_sources import load_active_sources  # type: ignore
            except ImportError:
                load_active_sources = None  # type: ignore

        rows = load_active_sources() if load_active_sources else []
        if not rows:
            print("WARN: parser_sources unreachable or empty — falling back to YAML channels")
            self._fallback_to_yaml_channels()
            return sum(
                1
                for ch, sn in self.channel_to_schema.items()
                if sn in self.schemas
            )

        self.channel_to_schema = {}
        tg_count = 0
        for r in rows:
            schema_name = _DEFAULT_SCHEMA_BY_TYPE.get(r.type, "real_estate")
            if schema_name not in self.schemas:
                continue
            self.channel_to_schema[r.identifier] = schema_name
            if r.type == "telegram_channel":
                tg_count += 1
        print(
            f"Loaded {len(self.channel_to_schema)} sources from DB "
            f"({tg_count} telegram channels active)"
        )
        return tg_count

    def _fallback_to_yaml_channels(self) -> None:
        """Repopulate channel_to_schema from each YAML schema's
        legacy ``channels:`` list. Used only when DB is unreachable."""
        self.channel_to_schema = {}
        for schema_name, schema in self.schemas.items():
            for channel in schema.get('channels', []) or []:
                self.channel_to_schema[channel] = schema_name

    def get_schema_for_channel(self, channel_username: str) -> Optional[Dict]:
        """Get schema definition for a given channel"""
        schema_name = self.channel_to_schema.get(channel_username)
        if schema_name:
            return self.schemas.get(schema_name)
        return None

    def get_schema_name_for_channel(self, channel_username: str) -> Optional[str]:
        """Get schema name for a given channel"""
        return self.channel_to_schema.get(channel_username)

    def list_schemas(self) -> List[str]:
        """List all loaded schema names"""
        return list(self.schemas.keys())

    def get_all_channels(self) -> List[str]:
        """Get list of all configured channels"""
        return list(self.channel_to_schema.keys())


class SchemaExtractor:
    """Extract data from messages based on schema definitions"""

    def __init__(self, schema: Dict):
        self.schema = schema
        self.fields = schema.get('fields', [])

    def extract(self, message, channel_username: str) -> Dict[str, Any]:
        """Extract structured data from message based on schema"""
        extracted = {}
        message_text = message.text if hasattr(message, 'text') else ''

        for field in self.fields:
            field_name = field.get('name')
            field_type = field.get('type')
            extraction_config = field.get('extraction', {})

            try:
                value = self._extract_field(
                    field_name,
                    field_type,
                    extraction_config,
                    message,
                    message_text,
                    channel_username
                )

                if value is not None:
                    extracted[field_name] = value

            except Exception as e:
                print(f"Error extracting field '{field_name}': {e}")

        return extracted

    def _extract_field(self, field_name: str, field_type: str,
                      extraction_config: Dict, message, message_text: str,
                      channel_username: str) -> Any:
        """Extract a single field value"""

        # Handle special sources
        source = extraction_config.get('source')
        if source:
            if source == 'message.text':
                return message_text
            elif source == 'message.id':
                return message.id
            elif source == 'message.date':
                return message.date.isoformat() if hasattr(message.date, 'isoformat') else str(message.date)
            elif source == 'channel.username':
                return channel_username
            elif source == 'message.photos':
                # Return count or indication of photos
                return True if message.photo else False

        # Pattern-based extraction
        patterns = extraction_config.get('patterns', [])
        if isinstance(patterns, str):
            patterns = [patterns]

        if patterns:
            for pattern in patterns:
                match = re.search(pattern, message_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)

                    # Apply mapping if defined
                    mapping = extraction_config.get('mapping', {})
                    if mapping:
                        for map_pattern, map_value in mapping.items():
                            if re.search(map_pattern, value, re.IGNORECASE):
                                return map_value

                    # Type conversion
                    return self._convert_type(value, field_type)

        # Fallback extraction
        fallback = extraction_config.get('fallback')
        if fallback == 'extract_first_line':
            first_line = message_text.split('\n')[0] if message_text else ''
            return first_line.strip()

        # Default value
        return extraction_config.get('default')

    def _convert_type(self, value: str, field_type: str) -> Any:
        """Convert extracted string to appropriate type"""
        if value is None:
            return None

        try:
            if field_type == 'integer':
                # Remove non-digit characters
                clean_value = re.sub(r'[^\d]', '', str(value))
                return int(clean_value) if clean_value else None

            elif field_type == 'decimal':
                # Remove everything except digits, dots, and commas
                clean_value = re.sub(r'[^\d.,]', '', str(value))
                # Replace comma with dot for decimal
                clean_value = clean_value.replace(',', '.')
                return float(clean_value) if clean_value else None

            elif field_type == 'string':
                return str(value).strip()

            elif field_type == 'text':
                return str(value).strip()

            elif field_type == 'datetime':
                # Handle datetime parsing
                if isinstance(value, datetime):
                    return value.isoformat()
                return str(value)

            elif field_type == 'array':
                # Return as list if not already
                if isinstance(value, list):
                    return value
                return [value] if value else []

            else:
                return value

        except Exception as e:
            print(f"Error converting '{value}' to {field_type}: {e}")
            return value

    def validate(self, extracted_data: Dict) -> tuple[bool, List[str]]:
        """Validate extracted data against schema requirements"""
        errors = []

        for field in self.fields:
            field_name = field.get('name')
            required = field.get('required', False)

            if required and (field_name not in extracted_data or extracted_data[field_name] is None):
                errors.append(f"Required field '{field_name}' is missing")

            # Type validation for enums
            if field.get('type') == 'enum' and field_name in extracted_data:
                allowed_values = field.get('values', [])
                if extracted_data[field_name] not in allowed_values:
                    errors.append(f"Field '{field_name}' has invalid value. Allowed: {allowed_values}")

        return len(errors) == 0, errors

    def get_validation_rules(self) -> Dict:
        """Get validation rules from schema"""
        return self.schema.get('validation', {})

    def get_processing_config(self) -> Dict:
        """Get post-processing configuration"""
        return self.schema.get('processing', {})


def categorize_by_keywords(text: str, categories: Dict[str, Dict]) -> Optional[str]:
    """Auto-categorize text based on keyword matching"""
    text_lower = text.lower()

    for category_name, category_config in categories.items():
        keywords = category_config.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return category_name

    return None


# Example usage
if __name__ == '__main__':
    loader = SchemaLoader()

    print("\n=== Loaded Schemas ===")
    for schema_name in loader.list_schemas():
        print(f"- {schema_name}")

    print("\n=== Channel Mapping ===")
    for channel in loader.get_all_channels():
        schema_name = loader.get_schema_name_for_channel(channel)
        print(f"@{channel} -> {schema_name}")

    # Test extraction
    print("\n=== Test Extraction ===")
    schema = loader.get_schema_for_channel('electronics_uz')
    if schema:
        extractor = SchemaExtractor(schema)

        # Mock message object
        class MockMessage:
            def __init__(self):
                self.text = """iPhone 15 Pro Max 256GB

Yangi, karobkada
Narx: 12.000.000 sum
Joylashuv: Toshkent, Chilonzor
Tel: +998 90 123 45 67"""
                self.id = 12345
                self.date = datetime.now()
                self.photo = True

        msg = MockMessage()
        extracted = extractor.extract(msg, 'electronics_uz')

        print("Extracted data:")
        for key, value in extracted.items():
            print(f"  {key}: {value}")

        is_valid, errors = extractor.validate(extracted)
        print(f"\nValidation: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            for error in errors:
                print(f"  - {error}")
