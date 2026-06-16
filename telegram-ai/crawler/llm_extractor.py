"""
LLM-Based Data Extraction with Schema-Aware Prompts
Uses Claude/GPT to extract structured data from diverse posting styles
Much better than regex patterns for varied formats!
"""

import anthropic
import openai
import json
import os
import re
import hashlib
import logging
from typing import Dict, Optional, Any, List
import yaml
from pathlib import Path
import time

from llm_config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    MAX_TOKENS,
    MAX_LLM_RETRIES,
    LLM_RETRY_DELAY,
    LLM_TIMEOUT_SECONDS,
    ENABLE_RESPONSE_CACHE,
    CACHE_DIR,
    CACHE_TTL_HOURS
)

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Extract structured data using LLMs with schema-specific prompts"""

    def __init__(self, provider: str = None):
        """Initialize LLM client.

        Args:
            provider: LLM provider override ('anthropic', 'openai', 'gemini').
                      Falls back to LLM_PROVIDER from llm_config if not specified.
        """
        self.provider = provider or LLM_PROVIDER

        if self.provider == 'anthropic':
            self.anthropic_client = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY,
                timeout=LLM_TIMEOUT_SECONDS
            )
            logger.info(f"✅ Initialized Anthropic client with model {ANTHROPIC_MODEL}")

        elif self.provider == 'openai':
            self.openai_client = openai.OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=LLM_TIMEOUT_SECONDS
            )
            logger.info(f"✅ Initialized OpenAI client with model {OPENAI_MODEL}")

        elif self.provider == 'gemini':
            import google.generativeai as genai
            api_key = GEMINI_API_KEY or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            genai.configure(api_key=api_key)
            model_name = os.environ.get('GEMINI_MODEL', GEMINI_MODEL)
            self.gemini_model = genai.GenerativeModel(model_name)
            self._genai = genai
            logger.info(f"✅ Initialized Gemini client with model {model_name}")

        elif self.provider == 'ollama':
            base_url = os.environ.get('OLLAMA_BASE_URL', OLLAMA_BASE_URL)
            self.ollama_client = openai.OpenAI(
                base_url=f"{base_url}/v1",
                api_key="ollama",
            )
            self.ollama_model = os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL)
            logger.info(f"✅ Initialized Ollama client with model {self.ollama_model} at {base_url}")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use 'anthropic', 'openai', 'gemini', or 'ollama'.")

        # Cache directory
        if ENABLE_RESPONSE_CACHE:
            self.cache_dir = Path(CACHE_DIR)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ===========================
    # Response Caching
    # ===========================

    def _cache_key(self, text: str, schema_name: str = '', channel: str = '') -> str:
        """Generate a cache key from message text, schema, and channel"""
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        key_input = f"{schema_name}:{channel}:{normalized}"
        return hashlib.sha256(key_input.encode('utf-8')).hexdigest()

    def _get_cached(self, text: str, schema_name: str = '', channel: str = '') -> Optional[Dict]:
        """Get cached extraction result if available and not expired"""
        if not ENABLE_RESPONSE_CACHE:
            return None
        try:
            key = self._cache_key(text, schema_name, channel)
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
                if age_hours < CACHE_TTL_HOURS:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.debug(f"Cache hit: {key[:12]}... (age: {age_hours:.1f}h)")
                    return data
                else:
                    cache_file.unlink()
                    logger.debug(f"Cache expired: {key[:12]}...")
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def _set_cached(self, text: str, result: Dict, schema_name: str = '', channel: str = ''):
        """Save extraction result to cache"""
        if not ENABLE_RESPONSE_CACHE:
            return
        try:
            key = self._cache_key(text, schema_name, channel)
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
            logger.debug(f"Cached result: {key[:12]}...")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    # ===========================
    # Forwarded Post Handling
    # ===========================

    # Patterns for forwarded message headers
    FORWARDED_PATTERNS = [
        r'^Forwarded from .*?\n',
        r'^Переслано от .*?\n',
        r'^Репост от .*?\n',
        r'^\[Forwarded\].*?\n',
        r'^📢\s*Репост.*?\n',
    ]

    def strip_forwarded_headers(self, text: str) -> str:
        """Remove forwarded message headers that could confuse extraction"""
        cleaned = text
        for pattern in self.FORWARDED_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    # ===========================
    # Few-Shot Example Selection
    # ===========================

    # Channel-to-group mapping for selecting relevant examples
    CHANNEL_GROUPS = {
        # Tashkent Russian channels → examples 1,2,7,8,9
        'tashkent_ru': {
            'channels': ['baburieltor', 'Kvartira_doma_Tashkent', 'Nedvijimosss',
                         'realtor_yunusov', 'grandestate2019', 'RealestTash',
                         'vitrinanedvizhimosti', 'arentash'],
            'examples': [1, 2, 7, 8, 9],
        },
        # Tashkent mixed channels → examples 3,4
        'tashkent_mixed': {
            'channels': ['realtor_alii'],
            'examples': [3, 4],
        },
        # Regional Uzbek channels → examples 5,6,10,11,12,13
        'regional_uz': {
            'channels': ['UyCharxiy9', 'Imkonuyjoysavdoo', 'ANDIJON_UYJOY',
                         'NAMANGAN_UYJOY_BOZORI'],
            'examples': [5, 6, 10, 11, 12, 13],
        },
    }

    def _get_relevant_examples(self, channel: Optional[str] = None) -> List[int]:
        """
        Select most relevant few-shot examples based on channel.
        Returns list of example numbers (1-indexed) to include.
        Always includes a diverse base set + channel-specific examples.
        """
        if not channel:
            # No channel info — return a diverse subset (one per group)
            return [1, 3, 5, 7, 12]

        channel_lower = channel.lower().lstrip('@')

        for group_name, group_info in self.CHANNEL_GROUPS.items():
            if channel_lower in [c.lower() for c in group_info['channels']]:
                # Return group-specific examples + 1 from each other group for diversity
                relevant = list(group_info['examples'])
                for other_name, other_info in self.CHANNEL_GROUPS.items():
                    if other_name != group_name:
                        relevant.append(other_info['examples'][0])
                return sorted(set(relevant))

        # Unknown channel — return diverse set
        return [1, 3, 5, 7, 12]

    # ===========================
    # Pre-filtering (saves API costs)
    # ===========================

    # Keywords that indicate a property listing (Uzbek + Russian)
    LISTING_KEYWORDS = [
        # Property types
        r'квартира', r'ховли', r'участка', r'uy\b', r'kvartira', r'xonadon',
        r'офис', r'магазин', r"do'kon", r'помещени',
        # Actions
        r'сотилади', r'sotiladi', r'продается', r'продаю', r'продажа',
        r'ijaraga', r'аренда', r'сдается', r'сдаётся', r'sutkalik', r'посуточно',
        # Price indicators
        r'нархи', r'narxi', r'цена', r'price', r'у\.е', r'y\.e',
        r'\$', r'dollar', r'сум', r"so'm",
        # Property details
        r'хона', r'xona', r'комнат', r'этаж', r'кават', r'qavat',
        r'кв\.?м', r'м2\b', r'm²', r'sotix', r'сотих', r'сотки',
        # Contact
        r'\+998', r'998\d{9}',
    ]

    # Patterns that indicate NON-listing content. A7 V2.0 extends this list to
    # filter buying-intent and services posts before they hit the LLM, saving
    # cost and keeping the queue clean.
    SKIP_PATTERNS = [
        r'^(https?://\S+)$',  # Just a URL
        r'^@\w+$',  # Just a channel mention
        r'подписывайтесь|обязательно подпишитесь|канал(га|ымыз)',  # Subscribe promo
        r'доброе утро|хайрли тонг|good morning',  # Greetings
        r'с праздником|табриклаймиз|поздравля',  # Congratulations
        r'результат.*голосования|опрос|сўров',  # Polls
        r'реклама|reklama|тарифы|прайс.*лист',  # Advertising/pricing for channel ads
        # A7 V2.0: buying-intent posts (looking-for, not selling)
        r'\bкуплю\b|\bищу\b|\bкуплем\b|sotib olaman|qidiramiz',
        # A7 V2.0: agent / service posts (not actual listings)
        r'услуги риелтора|услуги агента|xizmat(lar)?\b|услуги по|услуга\s+риэлтор',
        # A7 V2.0: renovation / repair services
        r'ремонт квартир|ремонт под ключ|та[ʼ\']?мирлаш xizmat|ta\'mir(lash)? xizmat',
    ]

    def is_listing_message(self, text: str) -> bool:
        """
        Quick pre-filter: check if message is likely a property listing.
        Uses keyword matching to avoid expensive LLM calls on non-listing content.

        Returns True if the message should be sent to LLM for extraction.
        """
        if not text or len(text.strip()) < 20:
            return False

        text_lower = text.lower()

        # Check skip patterns first
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, text_lower):
                logger.debug(f"Skipped by pattern: {pattern}")
                return False

        # Count listing keyword matches
        matches = 0
        for keyword in self.LISTING_KEYWORDS:
            if re.search(keyword, text_lower):
                matches += 1

        # Need at least 2 keyword matches to be considered a listing
        if matches >= 2:
            return True

        # If only 1 match but text is long enough, might still be a listing
        if matches == 1 and len(text) > 100:
            return True

        logger.debug(f"Pre-filter rejected: only {matches} keyword matches in {len(text)} chars")
        return False

    def classify_message(self, message_text: str) -> Dict:
        """
        Use LLM to classify message type when pre-filter is uncertain.
        Much cheaper than full extraction — uses minimal tokens.

        Returns:
            Dict with:
                is_listing: bool
                message_type: 'property_listing' | 'advertisement' | 'greeting' |
                              'news' | 'agent_promo' | 'other'
                confidence: float (0-1)
        """
        # Check classification cache
        cached = self._get_cached(message_text, schema_name='_classify', channel='')
        if cached is not None:
            logger.debug("Classification cache hit")
            return cached

        prompt = """Classify this Telegram channel message. Is it a PROPERTY LISTING (apartment/house/land for sale or rent)?

MESSAGE:
```
""" + message_text[:500] + """
```

Return JSON only:
{"is_listing": true/false, "message_type": "property_listing|advertisement|greeting|news|agent_promo|other", "confidence": 0.0-1.0}"""

        try:
            if self.provider == 'anthropic':
                response = self.anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=100,
                    temperature=0,
                    system="Classify Telegram messages as property listings or other content. Return JSON only.",
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text.strip()
            elif self.provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "Classify Telegram messages as property listings or other content. Return JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=100,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content.strip()
            elif self.provider == 'gemini':
                response = self.gemini_model.generate_content(
                    "Classify Telegram messages as property listings or other content. Return JSON only.\n\n" + prompt,
                    generation_config=self._genai.types.GenerationConfig(
                        temperature=0,
                        max_output_tokens=100,
                    ),
                )
                content = response.text.strip()
            elif self.provider == 'ollama':
                response = self.ollama_client.chat.completions.create(
                    model=self.ollama_model,
                    messages=[
                        {"role": "system", "content": "Classify Telegram messages as property listings or other content. Return JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=100,
                )
                content = response.choices[0].message.content.strip()
            else:
                return {"is_listing": True, "message_type": "unknown", "confidence": 0.5}

            # Clean and parse
            if content.startswith('```'):
                content = content.replace('```json', '').replace('```', '').strip()

            result = json.loads(content)
            logger.debug(f"Classification: {result}")

            # Cache the classification result
            self._set_cached(message_text, result, schema_name='_classify', channel='')

            return result

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Default to treating as listing to avoid missing data
            return {"is_listing": True, "message_type": "unknown", "confidence": 0.0}

    # ===========================
    # Extraction
    # ===========================

    def build_extraction_prompt(self, schema: Dict, message_text: str,
                               channel: Optional[str] = None) -> str:
        """
        Build schema-specific extraction prompt

        This is the key to good LLM extraction - detailed, clear instructions!
        """
        schema_name = schema.get('schema_name', 'unknown')
        schema_description = schema.get('description', '')
        fields = schema.get('fields', [])

        # Build field descriptions
        field_descriptions = []
        for field in fields:
            field_name = field.get('name')
            field_type = field.get('type')
            field_desc = field.get('description', '')
            required = field.get('required', False)

            # Get possible values for enums
            values_hint = ''
            if field_type == 'enum':
                values = field.get('values', [])
                values_hint = f" (must be one of: {', '.join(values)})"

            req_marker = "REQUIRED" if required else "optional"

            field_descriptions.append(
                f"  - {field_name} ({field_type}, {req_marker}): {field_desc}{values_hint}"
            )

        fields_text = "\n".join(field_descriptions)

        # Select relevant few-shot examples based on channel
        selected_example_ids = self._get_relevant_examples(channel)
        examples_text = self._build_examples_text(selected_example_ids)

        # Build the prompt
        prompt = f"""You are a real estate data extraction specialist for Uzbekistan property listings from Telegram channels.

SCHEMA: {schema_name}
DESCRIPTION: {schema_description}

FIELDS TO EXTRACT:
{fields_text}

CONTEXT:
These messages come from Uzbekistan real estate Telegram channels. Posts are written in Uzbek (Latin or Cyrillic script) or Russian, sometimes mixed. You must handle all three scripts fluently.

Common channel patterns:
- Emoji bullets separate sections (🏠🏢📍💰📞🔥💧⚡️✅)
- Prices in USD ($, у.е., dollar) or UZS (so'm, сум, sum, 🍋 = million UZS)
- Locations: Tashkent districts or regional cities (Andijan, Namangan, Fergana, Kokand)
- Phone numbers: Uzbek format +998 XX XXX XX XX (prefixes: 90, 91, 93, 94, 95, 97, 98, 99, 33, 50, 55, 77)
- "Иккиламчига берилмайди" = no agents/middlemen
- "Субсидия/ипотека" = mortgage/subsidy available
- "Каропка холатида" / "коробка" = shell condition (unfinished)
- "Евро ремонт" / "евро ЛЮКС" = euro-quality renovation
- "Подключ" = turnkey ready
- "Факат нахдга" = cash only
- "Келишамиз" / "торг" = negotiable

EXTRACTION RULES:
1. LANGUAGE PRESERVATION (CRITICAL — MUST FOLLOW):
   - "description" and "address" MUST remain in the ORIGINAL language of the listing.
   - If the post is in Russian → output Russian. If Uzbek Cyrillic → output Uzbek Cyrillic. If Uzbek Latin → output Uzbek Latin. If English → output English.
   - NEVER translate free-text fields to English. You are a structured extractor, NOT a translator.
   - Only enum fields use normalized English values: property_type, listing_type, currency, amenities.
2. Extract ONLY the fields listed above
3. For REQUIRED fields, extract a value or use null if truly missing
4. For optional fields, use null if not found
5. Return price as a plain number WITHOUT currency (currency goes in "currency" field)
6. Phone numbers: normalize to +998XXXXXXXXX format (no spaces/dashes). If number lacks +998 prefix, add it
7. For enums, map to the closest allowed value
8. Infer listing_type from context:
   - "sotiladi/продается/продаю/sotuv" = sale
   - "ijaraga/аренда/сдается/сдаётся" = rent
   - "sutkalik/посуточно" = daily_rent
   - If not explicit, default to "sale" (most channels are sale-focused)
9. Multiple phone numbers: return the FIRST one only
10. Ignore channel self-promotion text (@channel_name, "подписывайтесь", "RASMIY")
11. "description" should be a SHORT summary (max 100 chars) of the property condition and key features — in the ORIGINAL language (see Rule 1)
12. "detected_language": set to "ru" if the post is in Russian, "uz" if in Uzbek (Latin or Cyrillic), "en" if in English

PRICE PARSING (critical — channels use many different formats):
- "265.000 y.e./торг" or "265.000 у.е." → price: 265000, currency: "USD"
- "92.000 у.е." or "92 000 y.e" → price: 92000, currency: "USD"
- "110.500 у.е." → price: 110500, currency: "USD"
- "85 000$" or "85.000$" → price: 85000, currency: "USD"
- "33.500$ факат нахдга" → price: 33500, currency: "USD"
- "54.500$ ипотека бор" → price: 54500, currency: "USD"
- "350 mln so'm" or "350 mln" → price: 350000000, currency: "UZS"
- "330 мл" (мл = миллион) → price: 330000000, currency: "UZS"
- "6.000$" → price: 6000, currency: "USD"
- "9 600 000 сум (800)" → price: 800, currency: "USD" (parenthetical USD is the real price)
- "9.000.000сум (750)" → price: 750, currency: "USD"
- "7 800 000" (no currency, rental context) → price: 7800000, currency: "UZS"
- "33,000 🍋" or "12,000 🍋" → price: 33000 or 12000, currency: "USD" (🍋 in this context = dollar amount)
- "7,500 🍋" (with m² context, new build) → price: 7500000000, currency: "UZS" (🍋 = million UZS per unit)
- "170.000$ мин торг" → price: 170000, currency: "USD"
- "138.000у.е." → price: 138000, currency: "USD"
- "28000$" → price: 28000, currency: "USD"
- "40,000$" → price: 40000, currency: "USD"
- "20.500 💵" → price: 20500, currency: "USD"
- "90.000 💵 ками бор" → price: 90000, currency: "USD"
- "32.000 💵" → price: 32000, currency: "USD"

ROOM PARSING:
- "3 хона" / "3 хонали" / "3 хоналик" → rooms: 3
- "3-комнатная" / "3к" / "3 комн" / "3-комн." → rooms: 3
- "1 хона 2 хона квартиралар" → this is a listing for MULTIPLE unit types, use null
- "4/2/8" or "4/12/14" (rooms/floor/total or complex format) → rooms: 4
- "1в2 комнаты" → rooms: 2 (studio converted to 2)
- "3 хона 4 хона қилинган" → rooms: 4 (was 3, converted to 4)
- "2 хона (42 кв/м)" → rooms: 2, area_sqm: 42

AREA PARSING:
- "107м2" / "75м2" / "62м2" → area_sqm: 107, 75, 62
- "65 кв.м" / "86кв.м" → area_sqm: 65, 86
- "42 кв/м" → area_sqm: 42
- "120 m²" → area_sqm: 120
- "40 м²" / "50 м²" → area_sqm: 40, 50
- "4 сотих" / "4 Сотих" / "6 сотихлик" → area_sqm: 400, 600 (1 sotix/sotka = 100 m²)
- "16×25" (land dimensions) → area_sqm: 400
- "15х19.7 М" → area_sqm: 295.5

FLOOR PARSING:
- "4/12/14" → floor: 4, total_floors: 14 (first=rooms, second=floor, third=total floors for this format)
- "3/8/9" → floor: 3 is rooms, 8 is floor, 9 is total → floor: 8, total_floors: 9
- "8 этаж 16 этажли дом" → floor: 8, total_floors: 16
- "3/9 этаж" → floor: 3, total_floors: 9
- "6 этаж 9 этажли" → floor: 6, total_floors: 9
- "4 Каватли бино, 2-Кават" → floor: 2, total_floors: 4
- "9 Каватли бино, 6-этаж" → floor: 6, total_floors: 9
- "4-қаватлик уйнинг 1-каватида" → floor: 1, total_floors: 4
- "4-қаватлик уйнинг 4-каватида" → floor: 4, total_floors: 4
- "5 этаж 15 этажей" → floor: 5, total_floors: 15
- "2 Этажлик" (standalone, house) → total_floors: 2, floor: null

DISTRICT/ADDRESS (Uzbekistan locations):
Tashkent districts (normalize to Latin):
- "Юнусабад"/"Юнусабадский" → "Yunusobod"
- "Яшнабадский"/"Яшнабад" → "Yashnobod"
- "Мирабадский"/"Мирабад" → "Mirobod"
- "Мирзо Улугбек"/"Мирзо-Улугбекский" → "Mirzo Ulug'bek"
- "Яккасарайский"/"Яккасарай" → "Yakkasaroy"
- "Чилонзор" → "Chilonzor"
- "Сергели"/"СЕРГИЛИ" → "Sergeli"
- "Олмазор" → "Olmazor"
- "Шайхонтохур" → "Shayxontohur"
- "Учтепа" → "Uchtepa"

Tashkent sub-areas & landmarks (use as address, not district):
- "Ц-1", "Ц-5" → address: "Tsentr-1", "Tsentr-5" (central Tashkent areas)
- "Паркентский" → address includes "Parkentskiy"
- "Корзинка" → nearby Korzinka supermarket (landmark)
- "Индех" / "ИНДЕХ" → Indeks area
- "Греен Хаус" / "Green House" → residential complex name
- "ЖК Infinity" / "ЖК Muhtasham" / "ЖК Мадрид" → residential complex names (use in address)

Regional cities:
- "Андижон"/"Andijon" → district: "Andijon"
- "Наманган" → district: "Namangan"
- "Фарғона"/"Фергана"/"Farg'ona" → district: "Farg'ona"
- "Қўқон"/"Кўкон"/"Kokand" → district: "Qo'qon"
- "Марғилон" → district: "Marg'ilon"
- "Хўжаобод" → district: "Xo'jaobod"
- "Булокбоши"/"Булоқбоши" → district: "Buloqboshi"
- "Ахсикент" → district: "Axsikent"
- Sub-areas: MFY names, street names → put in address field

AMENITIES VOCABULARY:
Recognize these as amenities:
- "мебель"/"мебелью"/"жихозлар" → "furniture"
- "техника"/"техникой"/"ТЕХНИКОЙ" → "appliances"
- "евроремонт"/"Евро ЛЮКС"/"евро" → "euro renovation"
- "кондиционер"/"кондер" → "air conditioning"
- "лифт" → "elevator"
- "паркинг"/"парковка"/"машина жой" → "parking"
- "газ"/"Газ" → "gas"
- "сув"/"вода" → "water"
- "свет"/"электр" → "electricity"
- "канализация" → "sewage"
- "паровое отопление"/"отопления" → "heating"
- "хаммом"/"санузел" → "bathroom"
- "гардеробная" → "wardrobe room"
- "балкон" → "balcony"
- "ховли"/"hovli" → "yard"
- "мевали дарахтлари" → "fruit trees"
- "WiFi"/"домофон" → "wifi", "intercom"
- "посудомойка" → "dishwasher"
- "фильтр питьевой воды" → "water filter"
- "Акфа ром" → "AKFA windows"
- "огороди" → "garden"

===== REAL EXAMPLES FROM ACTUAL CHANNELS =====

{examples_text}

===== END OF EXAMPLES =====

Now extract from this message:

MESSAGE TEXT:
```
{message_text}
```

IMPORTANT: Return a JSON object with ALL extracted fields PLUS a "confidence" field (0.0-1.0) indicating how confident you are in the extraction quality.
- 0.9-1.0: Clear, well-structured listing with all key fields present
- 0.7-0.8: Most fields found but some ambiguity
- 0.5-0.6: Partial extraction, several fields missing or uncertain
- Below 0.5: Very uncertain, message may not be a proper listing

Return ONLY valid JSON. No explanation, no markdown, no code blocks. Just the raw JSON object.

YOUR EXTRACTION:"""

        return prompt

    # All 13 real examples from actual channels, indexed by number
    EXTRACTION_EXAMPLES = {
        1: {
            'label': '@realtor_yunusov (Russian, Tashkent center, structured)',
            'input': """КОМПЛЕКС "Oz Mahal Golden House" 4/12/14
Мирзо Улугбек район
Дархонтепа улица
ор-р: Новомосковская
Общая площадь: 107м2
2 санузла; гардеробная
Состояние: Евро ЛЮКС
Дизайнерский ремонт
Укомплектована/новая
Мебелью и ТЕХНИКОЙ
ЦЕНА: 265.000 y.e./торг
По вопросам пишите...
t.me/realtoryunusov
+998909564446
+998983084446""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 265000, "currency": "USD", "rooms": 4, "area_sqm": 107, "floor": 12, "total_floors": 14, "district": "Mirzo Ulug\'bek", "address": "Darxontepa ko\'chasi, Oz Mahal Golden House", "description": "Евро ЛЮКС ремонт, дизайнерская отделка, укомплектована мебелью и техникой", "amenities": ["euro renovation", "furniture", "appliances", "wardrobe room"], "contact_phone": "+998909564446", "images": null, "confidence": 0.95}}',
        },
        2: {
            'label': '@realtor_yunusov (Russian, secondary market)',
            'input': """ВТОРИЧКА! 3/8/9
Паркентский Корзинка
Яшнабадский район
Французская плани-ка
Площадь: панель 75м2
Состояние: с ремонтом
Вместе с обстановкой
Мебелью и ТЕХНИКОЙ
ЦЕНА: 92.000 у.е.
+998909564446
+998983084446""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 92000, "currency": "USD", "rooms": 3, "area_sqm": 75, "floor": 8, "total_floors": 9, "district": "Yashnobod", "address": "Parkentskiy, near Korzinka", "description": "Вторичка, французская планировка, панельный дом, с ремонтом и мебелью", "amenities": ["furniture", "appliances"], "contact_phone": "+998909564446", "images": null, "confidence": 0.9}}',
        },
        3: {
            'label': '@realtor_alii (mixed Uzbek-Russian, Sergeli, new build)',
            'input': """СЕРГИЛИ ИНДЕХ - ГРЕЕН ХАУС
1 хона 36м 9 этаж 9 этажли дом
Каропка холатида болинган уй
Нархи: 33.500$ факат нахдга
✅
+998990667616 +998950755585""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 33500, "currency": "USD", "rooms": 1, "area_sqm": 36, "floor": 9, "total_floors": 9, "district": "Sergeli", "address": "Indeks, Green House", "description": "Каропка холатида, факат нахдга", "amenities": [], "contact_phone": "+998990667616", "images": null, "confidence": 0.9}}',
        },
        4: {
            'label': '@realtor_alii (mixed, mortgage available)',
            'input': """СЕРГИЛИ СОКИН МАКОН МЕТРО 5
2 хона 63м 8 этаж 16 этажли дом
✅
Бош толов: 32.500$ банкда: 330 мл
Ойлик толов: 4.850.000 сумдан
Квартира сотилади срочно 🔥
Метро 5-бекат Чинор бекатига 2км
+998990667616 +998997453355""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 32500, "currency": "USD", "rooms": 2, "area_sqm": 63, "floor": 8, "total_floors": 16, "district": "Sergeli", "address": "Sokin Makon, near Metro 5 station, 2km from Chinor station", "description": "Срочно сотилади, ипотека бор, ойлик толов 4.850.000 сумдан", "amenities": [], "contact_phone": "+998990667616", "images": null, "confidence": 0.85}}',
        },
        5: {
            'label': '@ANDIJON_UYJOY (Uzbek Cyrillic, Andijan apartment)',
            'input': """🏢| #Квартира сотилади
🏬 4 Каватли бино
🏘 2-Кават, 2 хона (42 кв/м)
🔥 Газ, сув, свет, канализация бор
♨️ Паровое отопление
🛠 Ремонти яхши холатда
📂 Ҳужжатлари жойида
💰 Нархи: 28000$, келишамиз
☝️ Қолган тўлови йўқ
📞 +998771200998
📍 Андижон, Хўжаобод, Янги машина бозор якинида
@ANDIJON_UYJOY RASMIY 👈""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 28000, "currency": "USD", "rooms": 2, "area_sqm": 42, "floor": 2, "total_floors": 4, "district": "Andijon", "address": "Xo\'jaobod, near Yangi mashina bozor", "description": "Ремонти яхши холатда, паровое отопление, ҳужжатлари жойида, келишамиз", "amenities": ["gas", "water", "electricity", "sewage", "heating"], "contact_phone": "+998771200998", "images": null, "confidence": 0.95}}',
        },
        6: {
            'label': '@ANDIJON_UYJOY (Uzbek Cyrillic, house/hovli)',
            'input': """🏡| Булокбошида #Ховли сотилади
📏 4 Сотих, 1 хона + Ошхона
🛏 Жихозлар колади
➕ Суратдаги барча нарса колади
💦 Хаммом бор
✔️ 2-Этажли 8 та молга жой бор
🔥 Газ, сув, свет бор
📁 Хужжатлар жойида
💰 Нархи 40,000$ келишамиз
📍 Андижон вилояти, Булокбоши тумани, Мурувват кучаси 65-Уй.
📞 +998999827979
@ANDIJON_UYJOY RASMIY 👈""",
            'output': '{{"property_type": "house", "listing_type": "sale", "price": 40000, "currency": "USD", "rooms": 1, "area_sqm": 400, "floor": null, "total_floors": 2, "district": "Buloqboshi", "address": "Muruvvat ko\'chasi 65-uy, Buloqboshi tumani, Andijon viloyati", "description": "4 сотих, 2 этажли, 8 та молга жой, жихозлар колади, хаммом бор, хужжатлар жойида", "amenities": ["gas", "water", "electricity", "furniture", "bathroom", "yard"], "contact_phone": "+998999827979", "images": null, "confidence": 0.95}}',
        },
        7: {
            'label': '@arentash (Russian, Tashkent rental, structured)',
            'input': """Местонахождение: Мирабадский район. Перевушка. Ориентир ЖК "Infinity"
Количество комнат: 3
Общая площадь: 75
Этаж: 4
Этажность: 9
Цена: 9 600 000 сум (800) (коммунальные отдельно)
Предоплата: Нет
Депозит: 9 600 000 сум (800)
Что есть рядом: ЖК "Infinity", массив Эльбек, ресторан "Efendi", 145 школа
Номер: +998901120701 @power888 или +998901205885 @behruz_rieltor
Краткое описание:
Ремонт: Современный ремонт
Укомплектованная мебелью и техникой
WiFi и домофон в наличии
Санузел раздельный
Есть Посудомойка
Есть фильтр питьевой воды
Без животных!""",
            'output': '{{"property_type": "apartment", "listing_type": "rent", "price": 800, "currency": "USD", "rooms": 3, "area_sqm": 75, "floor": 4, "total_floors": 9, "district": "Mirobod", "address": "Perevushka, near JK Infinity", "description": "Современный ремонт, укомплектована мебелью и техникой, без животных, коммунальные отдельно", "amenities": ["furniture", "appliances", "wifi", "intercom", "dishwasher", "water filter"], "contact_phone": "+998901120701", "images": null, "confidence": 0.95}}',
        },
        8: {
            'label': '@grandestate2019 (Russian, Tashkent premium)',
            'input': """Ц-5, ориентир: Финансовый Институт
ЖК Muhtasham
Комнат: 3
Этаж: 10
Этажность: 11
Площадь: 72м²
Состояние: новый евроремонт, укомплектована мебелью и техникой Bosch
Цена: 138.000у.е. 🔥🔥🔥🔥
Срочно🔥🔥🔥🔥🔥🔥🔥🔥
+99898-077-55-55""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 138000, "currency": "USD", "rooms": 3, "area_sqm": 72, "floor": 10, "total_floors": 11, "district": "Mirobod", "address": "Tsentr-5, JK Muhtasham, near Financial Institute", "description": "Срочно, новый евроремонт, техника Bosch", "amenities": ["euro renovation", "furniture", "appliances"], "contact_phone": "+998980775555", "images": null, "confidence": 0.95}}',
        },
        9: {
            'label': '@grandestate2019 (Russian, elite)',
            'input': """ЭЛИТНЫЙ КОМПЛЕКС
ЖК «Инфинити»
Мирабадский район
Садык Азимова Эфенди
Вид на Эфенди
1в2 комнаты
5 этаж
15 этажей
ОБЩАЯ площадь: 43м2
Есть + отрытый балкон
Укомплектована/новая
ЦЕНА: 170.000$ мин торг
+99898-077-55-55""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 170000, "currency": "USD", "rooms": 2, "area_sqm": 43, "floor": 5, "total_floors": 15, "district": "Mirobod", "address": "Sadik Azimova, JK Infinity, Efendi area", "description": "Элитный комплекс, 1 в 2 комнаты, открытый балкон, укомплектована", "amenities": ["furniture", "balcony"], "contact_phone": "+998980775555", "images": null, "confidence": 0.9}}',
        },
        10: {
            'label': '@Imkonuyjoysavdoo (Uzbek Cyrillic, Fergana)',
            'input': """ЭЪЛОН✔️4️⃣4️⃣8️⃣1️⃣
🏬 #КВАРТИРА СОТИЛАДИ!
🔖 Манзил: Фарғона ш. Киргили Пелекан
🏬 4-қаватлик уйнинг
🏬 1-каватида
🏬 2 хоналик
🏬 Акфа ром
🏬 Огороди бор
🏬 Ремонти яхши
🏬 Документлари жойида
🔥💡💧 бор
💰 20.500 💵
❌ Иккиламчига берилмайди
📞 +998905621500""",
            'output': '{{"property_type": "apartment", "listing_type": "sale", "price": 20500, "currency": "USD", "rooms": 2, "area_sqm": null, "floor": 1, "total_floors": 4, "district": "Farg\'ona", "address": "Kirgili Pelekan", "description": "Ремонти яхши, Акфа ром, огороди бор, документлари жойида, иккиламчига берилмайди", "amenities": ["gas", "electricity", "water", "AKFA windows", "garden"], "contact_phone": "+998905621500", "images": null, "confidence": 0.9}}',
        },
        11: {
            'label': '@Imkonuyjoysavdoo (Uzbek, house)',
            'input': """ЭЪЛОН✔️4️⃣4️⃣7️⃣9️⃣
🏠 #ХОВЛИ ЖОЙ СОТИЛАДИ
🔖 Манзил: Фарғона ш. Аэрапорт Иподром котедж
🏠 6 сотихлик
🏠 4 хоналик
🏠 Ошхонаси алохида
🏠 2 та санузел
🏠 П-гиштлик
🏠 Алохида отопления қилинган
🏠 Атрофи тўлиқ ўралган
🏠 Мевали дарахтлари бор
🏠 Документлари жойида
🔥💡💧 бор
💰 90.000 💵 ками бор
❌ Иккиламчига берилмайди
📞 +998902906588""",
            'output': '{{"property_type": "house", "listing_type": "sale", "price": 90000, "currency": "USD", "rooms": 4, "area_sqm": 600, "floor": null, "total_floors": null, "district": "Farg\'ona", "address": "Aeroport Ipodrom kotej", "description": "6 сотих, п-гиштлик, ошхонаси алоҳида, 2 санузел, алоҳида отопления, мевали дарахтлар", "amenities": ["gas", "electricity", "water", "heating", "fruit trees", "bathroom"], "contact_phone": "+998902906588", "images": null, "confidence": 0.95}}',
        },
        12: {
            'label': '@NAMANGAN_UYJOY_BOZORI (Uzbek, Namangan house)',
            'input': """🏢| Ахсикентда #Ховли сотилади
📏 3 Сотих, 15х19.7 М
🏘 2 Этажлик, 6 хона
💦 Сув, свет бор
🔥 Газ махаллага келган
📁 Хужжатлари жойида
💰 Нархи 33,000 🍋 396 милён
📍 Ахсикент, Мингтеракда
📞 +998911829696""",
            'output': '{{"property_type": "house", "listing_type": "sale", "price": 33000, "currency": "USD", "rooms": 6, "area_sqm": 295.5, "floor": null, "total_floors": 2, "district": "Axsikent", "address": "Mingterak, Axsikent", "description": "3 сотих, 2 этажлик, газ маҳаллага келган, ҳужжатлари жойида", "amenities": ["water", "electricity"], "contact_phone": "+998911829696", "images": null, "confidence": 0.9}}',
        },
        13: {
            'label': '@NAMANGAN_UYJOY_BOZORI (Uzbek, land)',
            'input': """⛳️| #Участка сотилади
📏 4 Сотиҳ 16×25
🛠 Қуруқ ёр
✔️ Сув, свет бор
💰 Нархи 12,000$ Келишамиз
📍 Ахсикннт абдужаббор куприги богчани оркасидаги туткатор кучада
📞 +998997257179""",
            'output': '{{"property_type": "land", "listing_type": "sale", "price": 12000, "currency": "USD", "rooms": null, "area_sqm": 400, "floor": null, "total_floors": null, "district": "Axsikent", "address": "Abdujabbor ko\'prigi orqasidagi Tutqator ko\'chasi", "description": "Қуруқ ёр, 4 сотиҳ (16×25м), келишамиз", "amenities": ["water", "electricity"], "contact_phone": "+998997257179", "images": null, "confidence": 0.9}}',
        },
    }

    def _build_examples_text(self, example_ids: List[int]) -> str:
        """Build examples section from selected example IDs"""
        parts = []
        for i, eid in enumerate(example_ids, 1):
            ex = self.EXTRACTION_EXAMPLES.get(eid)
            if ex:
                parts.append(f"EXAMPLE {i} — {ex['label']}:\nINPUT:\n{ex['input']}\n\nOUTPUT:\n{ex['output']}")
        return "\n\n".join(parts)

    def extract_with_anthropic(self, prompt: str) -> Optional[Dict]:
        """Extract using Claude"""
        try:
            model = ANTHROPIC_MODEL

            logger.debug(f"Calling Claude {model}...")

            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                system="You are a real estate data extraction specialist for Uzbekistan property listings. You fluently read Uzbek (Latin and Cyrillic), Russian, and mixed-language posts. Extract structured data and return valid JSON only. Never include explanations or markdown. CRITICAL: Never translate user text. Keep description and address in the ORIGINAL language of the listing (Russian, Uzbek, etc.). Only enum fields (property_type, listing_type, currency, amenities) use English values.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()

            # Parse JSON
            extracted_data = json.loads(content)

            logger.debug(f"✅ Extraction successful with {model}")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            logger.error(f"Response content: {content}")
            return None

        except Exception as e:
            logger.error(f"Error calling Claude: {e}")
            return None

    def extract_with_openai(self, prompt: str) -> Optional[Dict]:
        """Extract using GPT"""
        try:
            logger.debug(f"Calling GPT {OPENAI_MODEL}...")

            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a real estate data extraction specialist for Uzbekistan property listings. You fluently read Uzbek (Latin and Cyrillic), Russian, and mixed-language posts. Extract structured data and return valid JSON only. Never include explanations or markdown. CRITICAL: Never translate user text. Keep description and address in the ORIGINAL language of the listing (Russian, Uzbek, etc.). Only enum fields (property_type, listing_type, currency, amenities) use English values."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"}  # Force JSON output
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            extracted_data = json.loads(content)

            logger.debug(f"✅ Extraction successful with GPT")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from GPT response: {e}")
            return None

        except Exception as e:
            logger.error(f"Error calling GPT: {e}")
            return None

    def extract_with_gemini(self, prompt: str) -> Optional[Dict]:
        """Extract using Google Gemini"""
        try:
            logger.debug(f"Calling Gemini {GEMINI_MODEL}...")

            response = self.gemini_model.generate_content(
                "You are a real estate data extraction specialist for Uzbekistan property listings. "
                "You fluently read Uzbek (Latin and Cyrillic), Russian, and mixed-language posts. "
                "Extract structured data and return valid JSON only. Never include explanations or markdown. "
                "CRITICAL: Never translate user text. Keep description and address in the ORIGINAL language "
                "of the listing (Russian, Uzbek, etc.). Only enum fields (property_type, listing_type, "
                "currency, amenities) use English values.\n\n" + prompt,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=LLM_TEMPERATURE,
                    max_output_tokens=MAX_TOKENS,
                ),
            )

            content = response.text.strip()

            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()

            extracted_data = json.loads(content)

            logger.debug(f"✅ Extraction successful with Gemini")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            return None

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return None

    def extract_with_ollama(self, prompt: str) -> Optional[Dict]:
        """Extract using local Ollama model"""
        try:
            logger.debug(f"Calling Ollama {self.ollama_model}...")

            response = self.ollama_client.chat.completions.create(
                model=self.ollama_model,
                messages=[
                    {"role": "system", "content": "You are a real estate data extraction specialist for Uzbekistan property listings. You fluently read Uzbek (Latin and Cyrillic), Russian, and mixed-language posts. Extract structured data and return valid JSON only. Never include explanations or markdown. CRITICAL: Never translate user text. Keep description and address in the ORIGINAL language of the listing (Russian, Uzbek, etc.). Only enum fields (property_type, listing_type, currency, amenities) use English values."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )

            content = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()

            extracted_data = json.loads(content)

            logger.debug(f"✅ Extraction successful with Ollama")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Ollama response: {e}")
            return None

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    def extract(self, schema: Dict, message_text: str, retry: bool = True,
                skip_prefilter: bool = False,
                channel: Optional[str] = None) -> Optional[Dict]:
        """
        Extract structured data from message using LLM

        Args:
            schema: Schema definition dict
            message_text: Raw message text
            retry: Whether to retry on failure
            skip_prefilter: Skip the pre-filter check
            channel: Channel username (for few-shot example selection)

        Returns:
            Dict with extracted fields, or None if extraction failed
        """
        # Strip forwarded message headers
        cleaned_text = self.strip_forwarded_headers(message_text)

        # Pre-filter: skip non-listing messages to save API costs
        if not skip_prefilter:
            if not self.is_listing_message(cleaned_text):
                # Use LLM classifier as fallback for borderline cases
                if len(cleaned_text) > 50:
                    classification = self.classify_message(cleaned_text)
                    if not classification.get('is_listing', False):
                        logger.info(f"Classifier rejected message: {classification.get('message_type', 'unknown')}")
                        return None
                    logger.info(f"Classifier accepted borderline message (confidence: {classification.get('confidence', 0)})")
                else:
                    logger.info(f"Pre-filter: skipped non-listing message ({len(cleaned_text)} chars)")
                    return None

        # Check cache
        schema_name = schema.get('schema_name', '')
        cached = self._get_cached(cleaned_text, schema_name=schema_name, channel=channel or '')
        if cached is not None:
            logger.info("Returning cached extraction result")
            return cached

        # Build prompt with channel-specific examples
        prompt = self.build_extraction_prompt(schema, cleaned_text, channel=channel)

        # Try extraction with retries
        for attempt in range(MAX_LLM_RETRIES if retry else 1):
            try:
                if self.provider == 'anthropic':
                    result = self.extract_with_anthropic(prompt)
                elif self.provider == 'openai':
                    result = self.extract_with_openai(prompt)
                elif self.provider == 'gemini':
                    result = self.extract_with_gemini(prompt)
                elif self.provider == 'ollama':
                    result = self.extract_with_ollama(prompt)
                else:
                    logger.error(f"Unsupported LLM provider: {self.provider}")
                    return None

                if result:
                    normalized = self.normalize_extraction(result)

                    # Validate against schema
                    is_valid, errors = self.validate_extraction(schema, normalized)
                    if not is_valid:
                        logger.warning(f"Validation errors: {errors}")
                        # Still return result but log issues — don't discard partial data

                    # Cache the result
                    self._set_cached(cleaned_text, normalized, schema_name=schema_name, channel=channel or '')

                    return normalized

                if attempt < MAX_LLM_RETRIES - 1:
                    logger.warning(f"Extraction failed, retrying ({attempt + 1}/{MAX_LLM_RETRIES})...")
                    time.sleep(LLM_RETRY_DELAY)

            except Exception as e:
                logger.error(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt < MAX_LLM_RETRIES - 1:
                    time.sleep(LLM_RETRY_DELAY)

        logger.error("All extraction attempts failed")
        return None

    def normalize_extraction(self, extracted_data: Dict) -> Dict:
        """
        Post-process and normalize LLM extraction output.
        Fixes common LLM mistakes and ensures consistent formatting.
        """
        data = dict(extracted_data)

        # Normalize phone number
        phone = data.get('contact_phone')
        if phone and isinstance(phone, str):
            # Remove all non-digit characters except leading +
            digits = re.sub(r'[^\d]', '', phone)
            if len(digits) == 9:
                digits = '998' + digits
            if len(digits) == 12 and digits.startswith('998'):
                data['contact_phone'] = '+' + digits
            elif len(digits) == 12:
                data['contact_phone'] = '+' + digits
            else:
                data['contact_phone'] = phone  # Leave as-is if can't normalize

        # Ensure price is numeric
        price = data.get('price')
        if price is not None:
            if isinstance(price, str):
                price_clean = re.sub(r'[^\d.]', '', str(price))
                try:
                    data['price'] = float(price_clean) if '.' in price_clean else int(price_clean)
                except (ValueError, TypeError):
                    data['price'] = None

        # Normalize currency
        currency = data.get('currency')
        if currency:
            currency_upper = str(currency).upper().strip()
            if currency_upper in ('$', 'USD', 'DOLLAR', 'У.Е.', 'Y.E.', 'Y.E', 'У.Е'):
                data['currency'] = 'USD'
            elif currency_upper in ('UZS', "SO'M", 'СУМ', 'SUM', 'SOM'):
                data['currency'] = 'UZS'

        # Ensure rooms is int or null
        rooms = data.get('rooms')
        if rooms is not None:
            try:
                data['rooms'] = int(rooms)
            except (ValueError, TypeError):
                data['rooms'] = None

        # Ensure area_sqm is float or null
        area = data.get('area_sqm')
        if area is not None:
            try:
                data['area_sqm'] = float(area)
            except (ValueError, TypeError):
                data['area_sqm'] = None

        # Ensure floor/total_floors are int or null
        for field in ('floor', 'total_floors'):
            val = data.get(field)
            if val is not None:
                try:
                    data[field] = int(val)
                except (ValueError, TypeError):
                    data[field] = None

        # Ensure amenities is a list
        amenities = data.get('amenities')
        if amenities is None:
            data['amenities'] = []
        elif isinstance(amenities, str):
            data['amenities'] = [a.strip() for a in amenities.split(',') if a.strip()]

        # Strip channel promo from description
        desc = data.get('description')
        if desc and isinstance(desc, str):
            desc = re.sub(r'@\w+', '', desc).strip()
            data['description'] = desc[:200]  # Cap length

        # Price sanity validation
        price = data.get('price')
        currency = data.get('currency')
        prop_type = data.get('property_type')
        if price is not None and isinstance(price, (int, float)):
            if currency == 'USD':
                # USD sanity ranges by property type
                ranges = {
                    'apartment': (500, 5_000_000),
                    'house': (1_000, 10_000_000),
                    'commercial': (1_000, 20_000_000),
                    'land': (100, 5_000_000),
                    'office': (1_000, 10_000_000),
                }
                min_p, max_p = ranges.get(prop_type, (100, 20_000_000))
                if price < min_p or price > max_p:
                    logger.warning(f"Price sanity check failed: ${price} for {prop_type} (expected ${min_p}-${max_p})")
                    data['_price_warning'] = f"Unusual price: ${price} for {prop_type}"
            elif currency == 'UZS':
                # UZS: rental ~5M-50M/month, sale ~100M-50B
                if data.get('listing_type') == 'rent':
                    if price < 1_000_000 or price > 500_000_000:
                        logger.warning(f"Price sanity check failed: {price} UZS rent")
                        data['_price_warning'] = f"Unusual rental price: {price} UZS"
                else:
                    if price < 10_000_000 or price > 100_000_000_000:
                        logger.warning(f"Price sanity check failed: {price} UZS sale")
                        data['_price_warning'] = f"Unusual sale price: {price} UZS"

        # Extract confidence (from LLM output)
        confidence = data.get('confidence')
        if confidence is not None:
            try:
                data['confidence'] = float(confidence)
            except (ValueError, TypeError):
                data['confidence'] = None

        return data

    def validate_extraction(self, schema: Dict, extracted_data: Dict) -> tuple[bool, list[str]]:
        """
        Validate extracted data against schema

        Args:
            schema: Schema definition
            extracted_data: Extracted data from LLM

        Returns:
            (is_valid, errors) tuple
        """
        errors = []

        # Check required fields
        for field in schema.get('fields', []):
            field_name = field.get('name')
            required = field.get('required', False)

            if required:
                if field_name not in extracted_data or extracted_data[field_name] is None:
                    errors.append(f"Required field '{field_name}' is missing")

            # Validate enum values
            if field.get('type') == 'enum' and field_name in extracted_data:
                value = extracted_data[field_name]
                if value is not None:
                    allowed_values = field.get('values', [])
                    if value not in allowed_values:
                        errors.append(f"Field '{field_name}' has invalid value '{value}'. Allowed: {allowed_values}")

        return len(errors) == 0, errors


# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    print("="*60)
    print("Testing LLM-Based Extraction")
    print("="*60)

    # Load a test schema
    schema_path = Path('schemas/real_estate.yaml')
    if schema_path.exists():
        with open(schema_path, 'r', encoding='utf-8') as f:
            test_schema = yaml.safe_load(f)

        # Test message (real Telegram channel format)
        test_message = """🏢| #Квартира сотилади
🏬 9 Каватли бино, 6-этаж
🏘 Умумий майдони 50 кв² 2 хона
➕ Лифт бор
🛠 Ремонти яхши холатда
🔥 Газ, сув, свет, атапилиня бор
📁 Хужжатлари жойида
💰 Нархи 6.000$
📍 Богишамол машина бозор олди
📞 +998500556804
@ANDIJON_UYJOY RASMIY 👈"""

        print("\n📄 Test Message:")
        print(test_message)
        print("\n" + "="*60)

        # Initialize extractor
        extractor = LLMExtractor()

        # Extract
        print("\n🤖 Extracting with LLM...")
        result = extractor.extract(test_schema, test_message)

        if result:
            print("\n✅ Extraction Successful!")
            print("\nExtracted Data:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Validate
            is_valid, errors = extractor.validate_extraction(test_schema, result)
            if is_valid:
                print("\n✅ Validation passed!")
            else:
                print("\n❌ Validation errors:")
                for error in errors:
                    print(f"  - {error}")
        else:
            print("\n❌ Extraction failed")

    else:
        print(f"\n⚠️  Schema file not found: {schema_path}")
        print("Run this from the crawler directory")

    print("\n" + "="*60)
