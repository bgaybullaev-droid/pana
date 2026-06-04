"""Uzbekistan regions and districts registry.

Single source of truth for valid region→district mappings.
Used by schemas for validation and migrations for data conversion.
"""

from typing import Optional

# Region key → list of district keys
REGIONS: dict[str, list[str]] = {
    "qoraqalpogiston": [
        "nukus_sh",
        "nukus_t",
        "amudaryo",
        "beruniy",
        "chimboy",
        "ellikqala",
        "kegeyli",
        "moynaq",
        "qanliko_l",
        "qo_ng_irot",
        "qorao_zak",
        "shumanay",
        "taxtako_pir",
        "to_rtko_l",
        "xo_jayli",
        "bo_zatov",
    ],
    "andijon": [
        "andijon_sh",
        "andijon_t",
        "asaka",
        "baliqchi",
        "bo_z",
        "buloqboshi",
        "izboskan",
        "jalaquduq",
        "xo_jaobod",
        "qo_rg_ontepa",
        "marhamat",
        "oltinko_l",
        "paxtaobod",
        "shahrixon",
        "ulug_nor",
        "xonobod",
    ],
    "buxoro": [
        "buxoro_sh",
        "buxoro_t",
        "g_ijduvon",
        "jondor",
        "kogon",
        "olot",
        "peshku",
        "qorako_l",
        "qorovulbozor",
        "romitan",
        "shofirkon",
        "vobkent",
    ],
    "fargona": [
        "fargona_sh",
        "fargona_t",
        "beshariq",
        "bog_dod",
        "dang_ara",
        "furqat",
        "yozyovon",
        "quva",
        "marg_ilon",
        "oltiariq",
        "o_zbekiston",
        "qo_shtepa",
        "quvasoy",
        "rishton",
        "so_x",
        "toshloq",
        "uchko_prik",
    ],
    "jizzax": [
        "jizzax_sh",
        "arnasoy",
        "baxmal",
        "do_stlik",
        "forish",
        "g_allaorol",
        "sharof_rashidov",
        "mirzacho_l",
        "paxtakor",
        "yangiobod",
        "zafarobod",
        "zarbdor",
        "zomin",
    ],
    "xorazm": [
        "urganch_sh",
        "urganch_t",
        "bog_ot",
        "gurlan",
        "xazorasp",
        "xiva",
        "xonqa",
        "qo_shko_pir",
        "shovot",
        "yangiariq",
        "yangibozor",
        "tuproqqala",
    ],
    "namangan": [
        "namangan_sh",
        "namangan_t",
        "chortoq",
        "chust",
        "kosonsoy",
        "mingbuloq",
        "norin",
        "pop",
        "to_raqo_rg_on",
        "uchqo_rg_on",
        "uychi",
        "yangiqo_rg_on",
    ],
    "navoiy": [
        "navoiy_sh",
        "karmana",
        "konimex",
        "navbahor",
        "nurota",
        "qiziltepa",
        "tomdi",
        "uchquduq",
        "xatirchi",
    ],
    "qashqadaryo": [
        "qarshi_sh",
        "qarshi_t",
        "chiroqchi",
        "dehqonobod",
        "g_uzor",
        "kasbi",
        "kitob",
        "ko_kdala",
        "mirishkor",
        "muborak",
        "nishon",
        "shahrisabz",
        "yakkabog_",
        "qamashi",
    ],
    "samarqand": [
        "samarqand_sh",
        "samarqand_t",
        "bulung_ur",
        "ishtixon",
        "jomboy",
        "kattaqo_rg_on",
        "narpay",
        "nurobod",
        "oqdaryo",
        "pastdarg_om",
        "payariq",
        "paxtachi",
        "toyloq",
        "urgut",
    ],
    "sirdaryo": [
        "guliston_sh",
        "guliston_t",
        "boyovut",
        "hovos",
        "mirzaobod",
        "oqoltin",
        "sardoba",
        "sayxunobod",
        "sirdaryo_t",
    ],
    "surxondaryo": [
        "termiz_sh",
        "termiz_t",
        "angor",
        "bandixon",
        "boysun",
        "denov",
        "jarqo_rg_on",
        "muzrabod",
        "oltinsoy",
        "qiziriq",
        "qumqo_rg_on",
        "sariosiyo",
        "sherobod",
        "sho_rchi",
        "uzun",
    ],
    "toshkent_viloyati": [
        "nurafshon",
        "olmaliq",
        "angren",
        "bekobod",
        "chirchiq",
        "ohangaron",
        "yangiyo_l",
        "bo_ka",
        "bo_stonliq",
        "chinoz",
        "qibray",
        "oqqo_rg_on",
        "parkent",
        "piskent",
        "toshkent_t",
        "zangiota",
        "yuqorichirchiq",
        "o_rtachirchiq",
        "quyi_chirchiq",
    ],
    "toshkent_shahri": [
        "bektemir",
        "chilonzor",
        "mirzo_ulugbek",
        "mirobod",
        "olmazor",
        "sergeli",
        "shayxontohur",
        "uchtepa",
        "yakkasaroy",
        "yashnobod",
        "yunusobod",
        "yangihayot",
    ],
}

# Flat set of all valid district keys
ALL_DISTRICTS: set[str] = set()
for _districts in REGIONS.values():
    ALL_DISTRICTS.update(_districts)

# Reverse lookup: district_key → region_key
DISTRICT_TO_REGION: dict[str, str] = {}
for _region, _districts in REGIONS.items():
    for _district in _districts:
        DISTRICT_TO_REGION[_district] = _region

# All valid region keys
VALID_REGIONS: set[str] = set(REGIONS.keys())

# Mapping of existing Russian district names → (region_key, district_key)
# Used by the migration to convert existing data
RUSSIAN_TO_KEY: dict[str, tuple[str, str]] = {
    "Мирзо-Улугбекский": ("toshkent_shahri", "mirzo_ulugbek"),
    "Яккасарайский": ("toshkent_shahri", "yakkasaroy"),
    "Чиланзарский": ("toshkent_shahri", "chilonzor"),
    "Сергелийский": ("toshkent_shahri", "sergeli"),
    "Юнусабадский": ("toshkent_shahri", "yunusobod"),
    "Шайхантаурский": ("toshkent_shahri", "shayxontohur"),
    "Учтепинский": ("toshkent_shahri", "uchtepa"),
    "Алмазарский": ("toshkent_shahri", "olmazor"),
    "Бектемирский": ("toshkent_shahri", "bektemir"),
    "Мирабадский": ("toshkent_shahri", "mirobod"),
    "Яшнабадский": ("toshkent_shahri", "yashnobod"),
}


# Fuzzy lookup: maps common crawler district spellings → district key
# Covers Latin, Cyrillic, mixed-case variants seen in OLX/Telegram data
_DISTRICT_ALIASES: dict[str, str] = {
    # toshkent_shahri districts
    "bektemir": "bektemir",
    "chilonzor": "chilonzor",
    "chilanзar": "chilonzor",
    "chilanzar": "chilonzor",
    "mirzo_ulugbek": "mirzo_ulugbek",
    "mirzo ulug'bek": "mirzo_ulugbek",
    "mirzo ulugbek": "mirzo_ulugbek",
    "mirzo-ulugbekskiy rayon": "mirzo_ulugbek",
    "мирзо-улугбекский район": "mirzo_ulugbek",
    "мирзо-улугбекский": "mirzo_ulugbek",
    "mirobod": "mirobod",
    "mirabad": "mirobod",
    "мирабадский": "mirobod",
    "olmazor": "olmazor",
    "алмазарский": "olmazor",
    "yangihayot": "yangihayot",
    "yangixayot": "yangihayot",
    "янгихаётский": "yangihayot",
    "sergeli": "sergeli",
    "sergili": "sergeli",
    "сергелийский": "sergeli",
    "shayxontohur": "shayxontohur",
    "shaykhontohur": "shayxontohur",
    "шайхантаурский": "shayxontohur",
    "uchtepa": "uchtepa",
    "учтепинский": "uchtepa",
    "yakkasaroy": "yakkasaroy",
    "yakkasaray": "yakkasaroy",
    "яккасарайский": "yakkasaroy",
    "yashnobod": "yashnobod",
    "яшнабадский": "yashnobod",
    "yunusobod": "yunusobod",
    "yunusabad": "yunusobod",
    "юнусабадский": "yunusobod",
    # toshkent_viloyati
    "chirchiq": "chirchiq",
    "olmaliq": "olmaliq",
    "angren": "angren",
    "nurafshon": "nurafshon",
    # andijon
    "andijon": "andijon_sh",
    "andijan": "andijon_sh",
    "asaka": "asaka",
    "buloqboshi": "buloqboshi",
    "bulokboshi": "buloqboshi",
    "xo'jaobod": "xo_jaobod",
    "xojaobod": "xo_jaobod",
    # samarqand
    "samarqand": "samarqand_sh",
    "samarkand": "samarqand_sh",
    # namangan
    "namangan": "namangan_sh",
    # fargona
    "fargona": "fargona_sh",
    "fergana": "fargona_sh",
    # buxoro
    "buxoro": "buxoro_sh",
    "bukhara": "buxoro_sh",
    # other cities used as districts
    "nukus": "nukus_sh",
    "qarshi": "qarshi_sh",
    "termiz": "termiz_sh",
    "termez": "termiz_sh",
    "urganch": "urganch_sh",
    "jizzax": "jizzax_sh",
    "jizzakh": "jizzax_sh",
    "navoiy": "navoiy_sh",
    "navoi": "navoiy_sh",
    "guliston": "guliston_sh",
    # Sub-district / mahalla level names
    "darhan": "zangiota",
    "g'ormiron": "kosonsoy",
}


# Landmark / address keyword → (district_key, region_key)
# Fallback when the crawler extracts an address but no district.
# Keys are lowercase substrings matched against the normalized address field.
_ADDRESS_LANDMARKS: dict[str, tuple[str, str]] = {
    # toshkent_shahri
    "akay city": ("sergeli", "toshkent_shahri"),
    "basri baba": ("sergeli", "toshkent_shahri"),
    "basribaba": ("sergeli", "toshkent_shahri"),
    "poytaxt gavhari": ("sergeli", "toshkent_shahri"),
    "mahtumkuli": ("yakkasaroy", "toshkent_shahri"),
    "махтумкули": ("yakkasaroy", "toshkent_shahri"),
    "mahtu": ("yakkasaroy", "toshkent_shahri"),
    "ipak yuli": ("mirzo_ulugbek", "toshkent_shahri"),
    "ipak yo'li": ("mirzo_ulugbek", "toshkent_shahri"),
    "ипак йули": ("mirzo_ulugbek", "toshkent_shahri"),
    "parkentsk": ("mirzo_ulugbek", "toshkent_shahri"),
    "alaisky": ("yakkasaroy", "toshkent_shahri"),
    "alaysk": ("yakkasaroy", "toshkent_shahri"),
    "алайский": ("yakkasaroy", "toshkent_shahri"),
    "financial institute": ("yakkasaroy", "toshkent_shahri"),
    "sayahat": ("chilonzor", "toshkent_shahri"),
    "sayohat": ("chilonzor", "toshkent_shahri"),
    "anhor": ("mirobod", "toshkent_shahri"),
    "анхор": ("mirobod", "toshkent_shahri"),
    "german embassy": ("mirobod", "toshkent_shahri"),
    "orikzor": ("uchtepa", "toshkent_shahri"),
    "урикзор": ("uchtepa", "toshkent_shahri"),
    # toshkent_viloyati
    "darxan": ("zangiota", "toshkent_viloyati"),
    "дархан": ("zangiota", "toshkent_viloyati"),
    # andijon
    "клара цеткин": ("andijon_sh", "andijon"),
    "klara tsetkin": ("andijon_sh", "andijon"),
    # qashqadaryo
    "koson": ("qamashi", "qashqadaryo"),
    "косон": ("qamashi", "qashqadaryo"),
}


def infer_region(district: Optional[str]) -> Optional[str]:
    """Infer region key from a crawler district string.

    Tries exact key match first, then fuzzy alias lookup.
    Returns the region key (e.g. 'toshkent_shahri') or None.
    """
    if not district:
        return None

    # 1. Exact match against canonical district keys
    if district in DISTRICT_TO_REGION:
        return DISTRICT_TO_REGION[district]

    # 2. Normalize and try alias lookup
    normalized = district.lower().strip()
    alias_key = _DISTRICT_ALIASES.get(normalized)
    if alias_key and alias_key in DISTRICT_TO_REGION:
        return DISTRICT_TO_REGION[alias_key]

    # 3. Try underscore-normalized form (e.g. "Mirzo Ulug'bek" → "mirzo_ulugbek")
    slug = (
        normalized.replace(" ", "_")
        .replace("'", "_")
        .replace("\u2019", "_")
        .replace("-", "_")
    )
    if slug in DISTRICT_TO_REGION:
        return DISTRICT_TO_REGION[slug]

    # 4. Fallback: district string is actually a region/city name (e.g. "Tashkent")
    _REGION_NAME_ALIASES: dict[str, str] = {
        "tashkent": "toshkent_shahri",
        "toshkent": "toshkent_shahri",
        "ташкент": "toshkent_shahri",
    }
    region = _REGION_NAME_ALIASES.get(normalized) or _REGION_NAME_ALIASES.get(slug)
    if region and region in VALID_REGIONS:
        return region

    return None


def infer_district_from_address(address: Optional[str]) -> Optional[tuple[str, str]]:
    """Infer (district_key, region_key) from an address/landmark string.

    Fallback used when the crawler provides an address but no district.
    Scans for known landmark substrings. Returns tuple or None.
    """
    if not address:
        return None

    normalized = address.lower().strip()

    for keyword, district_region in _ADDRESS_LANDMARKS.items():
        if keyword in normalized:
            return district_region

    return None


def validate_region_district(region: Optional[str], district: Optional[str]) -> bool:
    """Validate that the district belongs to the given region.

    Rules:
    - Both None → valid (no location specified)
    - Region only → valid (district optional)
    - District only → valid if district exists in any region
    - Both provided → district must belong to that region
    """
    if not region and not district:
        return True
    if region and not district:
        return region in VALID_REGIONS
    if district and not region:
        return district in ALL_DISTRICTS
    # Both provided
    if region not in VALID_REGIONS:
        return False
    return district in REGIONS.get(region, [])
