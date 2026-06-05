/**
 * Uzbekistan regions and districts — single source of truth.
 *
 * Keys are stable identifiers stored in the database.
 * Display names come from i18n (common:locations.region.* / common:locations.district.*).
 */

export interface RegionData {
  key: string;
  districts: string[];
}

export const REGIONS: RegionData[] = [
  {
    key: 'toshkent_shahri',
    districts: [
      'bektemir', 'chilonzor', 'mirzo_ulugbek', 'mirobod',
      'olmazor', 'sergeli', 'shayxontohur', 'uchtepa',
      'yakkasaroy', 'yashnobod', 'yunusobod', 'yangihayot',
    ],
  },
  {
    key: 'toshkent_viloyati',
    districts: [
      'nurafshon_sh', 'olmaliq_sh', 'angren_sh', 'bekobod_sh',
      'chirchiq_sh', 'ohangaron_sh', 'yangiyo_l_sh', 'bekobod_t',
      'ohangaron_t', 'yangiyo_l_t', 'bo_ka', 'bo_stonliq',
      'chinoz', 'qibray', 'oqqo_rg_on', 'parkent',
      'piskent', 'toshkent_t', 'zangiota', 'yuqorichirchiq',
      'o_rtachirchiq', 'quyi_chirchiq',
    ],
  },
  {
    key: 'andijon',
    districts: [
      'andijon_sh', 'xonobod_sh', 'andijon_t', 'asaka',
      'baliqchi', 'bo_ston', 'buloqboshi', 'izboskan',
      'jalaquduq', 'xo_jaobod', 'qo_rg_ontepa', 'marhamat',
      'oltinko_l', 'paxtaobod', 'shahrixon', 'ulug_nor',
    ],
  },
  {
    key: 'buxoro',
    districts: [
      'buxoro_sh', 'kogon_sh', 'buxoro_t', 'g_ijduvon',
      'jondor', 'kogon_t', 'olot', 'peshku',
      'qorako_l', 'qorovulbozor', 'romitan', 'shofirkon',
      'vobkent',
    ],
  },
  {
    key: 'fargona',
    districts: [
      'fargona_sh', 'qo_qon_sh', 'marg_ilon_sh', 'quvasoy_sh',
      'fargona_t', 'beshariq', 'bog_dod', 'buvayda',
      'dang_ara', 'furqat', 'yozyovon', 'quva',
      'oltiariq', 'o_zbekiston', 'qo_shtepa', 'rishton',
      'so_x', 'toshloq', 'uchko_prik',
    ],
  },
  {
    key: 'jizzax',
    districts: [
      'jizzax_sh', 'arnasoy', 'baxmal', 'do_stlik',
      'forish', 'g_allaorol', 'sharof_rashidov',
      'mirzacho_l', 'paxtakor', 'yangiobod', 'zafarobod',
      'zarbdor', 'zomin',
    ],
  },
  {
    key: 'namangan',
    districts: [
      'namangan_sh', 'namangan_t', 'chortoq', 'chust',
      'kosonsoy', 'mingbuloq', 'norin', 'pop',
      'to_raqo_rg_on', 'uchqo_rg_on', 'uychi', 'yangiqo_rg_on',
    ],
  },
  {
    key: 'navoiy',
    districts: [
      'navoiy_sh', 'zarafshon_sh', 'g_ozg_on_sh', 'karmana',
      'konimex', 'navbahor', 'nurota', 'qiziltepa',
      'tomdi', 'uchquduq', 'xatirchi',
    ],
  },
  {
    key: 'qashqadaryo',
    districts: [
      'qarshi_sh', 'shahrisabz_sh', 'qarshi_t', 'chiroqchi',
      'dehqonobod', 'g_uzor', 'kasbi', 'kitob',
      'ko_kdala', 'koson', 'mirishkor', 'muborak',
      'nishon', 'shahrisabz_t', 'yakkabog_', 'qamashi',
    ],
  },
  {
    key: 'qoraqalpogiston',
    districts: [
      'nukus_sh', 'nukus_t', 'amudaryo', 'beruniy',
      'chimboy', 'ellikqala', 'kegeyli', 'moynaq',
      'qanliko_l', 'qo_ng_irot', 'qorao_zak', 'shumanay',
      'taxiatosh', 'taxtako_pir', 'to_rtko_l', 'xo_jayli',
      'bo_zatov',
    ],
  },
  {
    key: 'samarqand',
    districts: [
      'samarqand_sh', 'kattaqo_rg_on_sh', 'samarqand_t', 'kattaqo_rg_on_t',
      'bulung_ur', 'ishtixon', 'jomboy', 'narpay',
      'nurobod', 'oqdaryo', 'pastdarg_om', 'payariq',
      'paxtachi', 'qo_shrabot', 'toyloq', 'urgut',
    ],
  },
  {
    key: 'sirdaryo',
    districts: [
      'guliston_sh', 'shirin_sh', 'yangiyer_sh', 'guliston_t',
      'boyovut', 'hovos', 'mirzaobod', 'oqoltin',
      'sardoba', 'sayxunobod', 'sirdaryo_t',
    ],
  },
  {
    key: 'surxondaryo',
    districts: [
      'termiz_sh', 'termiz_t', 'angor', 'bandixon',
      'boysun', 'denov', 'jarqo_rg_on', 'muzrabod',
      'oltinsoy', 'qiziriq', 'qumqo_rg_on', 'sariosiyo',
      'sherobod', 'sho_rchi', 'uzun',
    ],
  },
  {
    key: 'xorazm',
    districts: [
      'urganch_sh', 'xiva_sh', 'urganch_t', 'bog_ot',
      'gurlan', 'xazorasp', 'xiva_t', 'xonqa',
      'qo_shko_pir', 'shovot', 'yangiariq', 'yangibozor',
      'tuproqqala',
    ],
  },
];

// Precomputed lookup maps
const _regionMap = new Map<string, string[]>();
const _districtToRegion = new Map<string, string>();

for (const r of REGIONS) {
  _regionMap.set(r.key, r.districts);
  for (const d of r.districts) {
    _districtToRegion.set(d, r.key);
  }
}

/** Get district keys for a region */
export function getDistrictsForRegion(regionKey: string): string[] {
  return _regionMap.get(regionKey) ?? [];
}

/** Get all region keys */
export function getRegionKeys(): string[] {
  return REGIONS.map((r) => r.key);
}

export function normalizeLocationKey(key: string | null | undefined, type: 'region' | 'district' = 'district'): string {
  if (!key) return '';
  let normalized = key.toLowerCase().replace(/['`’]/g, '').replace(/[\s-]/g, '_');
  
  const aliases = type === 'region' ? REGION_ALIASES : DISTRICT_ALIASES;
  if (aliases[normalized]) {
    normalized = aliases[normalized];
  }
  return normalized;
}

/** Look up the region a district belongs to */
export function getRegionForDistrict(districtKey: string | null | undefined): string | undefined {
  if (!districtKey) return undefined;
  const normalized = normalizeLocationKey(districtKey, 'district');
  return _districtToRegion.get(normalized);
}

const REGION_ALIASES: Record<string, string> = {
  'samarkand': 'samarqand',
  'bukhara': 'buxoro',
  'fergana': 'fargona',
  'tashkent': 'toshkent_shahri',
  'tashkent_city': 'toshkent_shahri',
};

const DISTRICT_ALIASES: Record<string, string> = {
  'yashnabad': 'yashnobod',
  'yunusabad': 'yunusobod',
  'mirobad': 'mirobod',
  'almazar': 'olmazor',
  'almazarki': 'olmazor',
  'chilonzar': 'chilonzor',
  'chilanzar': 'chilonzor',
  'shayhantahur': 'shayxontohur',
  'shaynabad': 'shayxontohur', // common typo
  'samarkand': 'samarqand_sh',
  'bukhara': 'buxoro_sh',
  'fergana': 'fargona_sh',
  'tashkent': 'toshkent_shahri',
  'tashkent_city': 'toshkent_shahri',
  'yakkasaray': 'yakkasaroy',
  'yangikhayot': 'yangihayot',
};

/**
 * Translate a region key to a display name.
 * Falls back to the raw key for unknown values (e.g., crawler data).
 */
export function translateRegion(
  key: string | null | undefined,
  t: (k: string, options?: Record<string, unknown>) => string,
): string {
  if (!key) return '';
  const normalizedKey = normalizeLocationKey(key, 'region');
  const result = t(`common:locations.region.${normalizedKey}`, { defaultValue: '' });
  return result || key;
}

/**
 * Translate a district key to a display name.
 * Falls back to the raw key for unknown values (e.g., crawler data).
 */
export function translateDistrict(
  key: string | null | undefined,
  t: (k: string, options?: Record<string, unknown>) => string,
): string {
  if (!key) return '';
  const normalizedKey = normalizeLocationKey(key, 'district');
  const result = t(`common:locations.district.${normalizedKey}`, { defaultValue: '' });
  return result || key;
}
