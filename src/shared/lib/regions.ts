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
      'yakkasaroy', 'yashnobod', 'yunusobod',
    ],
  },
  {
    key: 'toshkent_viloyati',
    districts: [
      'nurafshon', 'olmaliq', 'angren', 'bekobod',
      'chirchiq', 'ohangaron', 'yangiyo_l',
      'bo_ka', 'bo_stonliq', 'chinoz', 'qibray',
      'oqqo_rg_on', 'parkent', 'piskent', 'toshkent_t',
      'zangiota', 'yuqorichirchiq', 'o_rtachirchiq',
      'quyi_chirchiq',
    ],
  },
  {
    key: 'andijon',
    districts: [
      'andijon_sh', 'andijon_t', 'asaka', 'baliqchi', 'bo_z',
      'buloqboshi', 'izboskan', 'jalaquduq', 'xo_jaobod',
      'qo_rg_ontepa', 'marhamat', 'oltinko_l', 'paxtaobod',
      'shahrixon', 'ulug_nor', 'xonobod',
    ],
  },
  {
    key: 'buxoro',
    districts: [
      'buxoro_sh', 'buxoro_t', 'g_ijduvon', 'jondor', 'kogon',
      'olot', 'peshku', 'qorako_l', 'qorovulbozor',
      'romitan', 'shofirkon', 'vobkent',
    ],
  },
  {
    key: 'fargona',
    districts: [
      'fargona_sh', 'fargona_t', 'beshariq', 'bog_dod',
      'dang_ara', 'furqat', 'yozyovon', 'quva', 'marg_ilon',
      'oltiariq', 'o_zbekiston', 'qo_shtepa', 'quvasoy',
      'rishton', 'so_x', 'toshloq', 'uchko_prik',
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
      'navoiy_sh', 'karmana', 'konimex', 'navbahor',
      'nurota', 'qiziltepa', 'tomdi', 'uchquduq',
      'xatirchi',
    ],
  },
  {
    key: 'qashqadaryo',
    districts: [
      'qarshi_sh', 'qarshi_t', 'chiroqchi', 'dehqonobod',
      'g_uzor', 'kasbi', 'kitob', 'ko_kdala',
      'mirishkor', 'muborak', 'nishon', 'shahrisabz',
      'yakkabog_', 'qamashi',
    ],
  },
  {
    key: 'qoraqalpogiston',
    districts: [
      'nukus_sh', 'nukus_t', 'amudaryo', 'beruniy', 'chimboy',
      'ellikqala', 'kegeyli', 'moynaq', 'qanliko_l', 'qo_ng_irot',
      'qorao_zak', 'shumanay', 'taxtako_pir', 'to_rtko_l', 'xo_jayli',
      'bo_zatov',
    ],
  },
  {
    key: 'samarqand',
    districts: [
      'samarqand_sh', 'samarqand_t', 'bulung_ur', 'ishtixon',
      'jomboy', 'kattaqo_rg_on', 'narpay', 'nurobod',
      'oqdaryo', 'pastdarg_om', 'payariq', 'paxtachi',
      'toyloq', 'urgut',
    ],
  },
  {
    key: 'sirdaryo',
    districts: [
      'guliston_sh', 'guliston_t', 'boyovut', 'hovos',
      'mirzaobod', 'oqoltin', 'sardoba', 'sayxunobod',
      'sirdaryo_t',
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
      'urganch_sh', 'urganch_t', 'bog_ot', 'gurlan',
      'xazorasp', 'xiva', 'xonqa', 'qo_shko_pir',
      'shovot', 'yangiariq', 'yangibozor', 'tuproqqala',
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

/** Look up the region a district belongs to */
export function getRegionForDistrict(districtKey: string): string | undefined {
  return _districtToRegion.get(districtKey);
}

/**
 * Translate a region key to a display name.
 * Falls back to the raw key for unknown values (e.g., crawler data).
 */
export function translateRegion(
  key: string | null | undefined,
  t: (k: string, options?: Record<string, unknown>) => string,
): string {
  if (!key) return '';
  const result = t(`common:locations.region.${key}`, { defaultValue: '' });
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
  const result = t(`common:locations.district.${key}`, { defaultValue: '' });
  return result || key;
}
