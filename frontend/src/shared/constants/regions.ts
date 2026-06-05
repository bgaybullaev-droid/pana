/**
 * Uzbekistan regions and districts registry.
 * Mirrors backend/app/core/regions.py — keep in sync.
 */
import type { TFunction } from 'i18next';

export const REGIONS: Record<string, string[]> = {
  toshkent_shahri: [
    'bektemir', 'chilonzor', 'mirzo_ulugbek', 'mirobod',
    'olmazor', 'sergeli', 'shayxontohur', 'uchtepa',
    'yakkasaroy', 'yashnobod', 'yunusobod', 'yangihayot',
  ],
  toshkent_viloyati: [
    'nurafshon_sh', 'olmaliq_sh', 'angren_sh', 'bekobod_sh',
    'chirchiq_sh', 'ohangaron_sh', 'yangiyo_l_sh', 'bekobod_t',
    'ohangaron_t', 'yangiyo_l_t', 'bo_ka', 'bo_stonliq',
    'chinoz', 'qibray', 'oqqo_rg_on', 'parkent',
    'piskent', 'toshkent_t', 'zangiota', 'yuqorichirchiq',
    'o_rtachirchiq', 'quyi_chirchiq',
  ],
  samarqand: [
    'samarqand_sh', 'kattaqo_rg_on_sh', 'samarqand_t', 'kattaqo_rg_on_t',
    'bulung_ur', 'ishtixon', 'jomboy', 'narpay',
    'nurobod', 'oqdaryo', 'pastdarg_om', 'payariq',
    'paxtachi', 'qo_shrabot', 'toyloq', 'urgut',
  ],
  buxoro: [
    'buxoro_sh', 'kogon_sh', 'buxoro_t', 'g_ijduvon',
    'jondor', 'kogon_t', 'olot', 'peshku',
    'qorako_l', 'qorovulbozor', 'romitan', 'shofirkon',
    'vobkent',
  ],
  andijon: [
    'andijon_sh', 'xonobod_sh', 'andijon_t', 'asaka',
    'baliqchi', 'bo_ston', 'buloqboshi', 'izboskan',
    'jalaquduq', 'xo_jaobod', 'qo_rg_ontepa', 'marhamat',
    'oltinko_l', 'paxtaobod', 'shahrixon', 'ulug_nor',
  ],
  fargona: [
    'fargona_sh', 'qo_qon_sh', 'marg_ilon_sh', 'quvasoy_sh',
    'fargona_t', 'beshariq', 'bog_dod', 'buvayda',
    'dang_ara', 'furqat', 'yozyovon', 'quva',
    'oltiariq', 'o_zbekiston', 'qo_shtepa', 'rishton',
    'so_x', 'toshloq', 'uchko_prik',
  ],
  namangan: [
    'namangan_sh', 'namangan_t', 'chortoq', 'chust',
    'kosonsoy', 'mingbuloq', 'norin', 'pop',
    'to_raqo_rg_on', 'uchqo_rg_on', 'uychi', 'yangiqo_rg_on',
  ],
  qashqadaryo: [
    'qarshi_sh', 'shahrisabz_sh', 'qarshi_t', 'chiroqchi',
    'dehqonobod', 'g_uzor', 'kasbi', 'kitob',
    'ko_kdala', 'koson', 'mirishkor', 'muborak',
    'nishon', 'shahrisabz_t', 'yakkabog_', 'qamashi',
  ],
  surxondaryo: [
    'termiz_sh', 'termiz_t', 'angor', 'bandixon',
    'boysun', 'denov', 'jarqo_rg_on', 'muzrabod',
    'oltinsoy', 'qiziriq', 'qumqo_rg_on', 'sariosiyo',
    'sherobod', 'sho_rchi', 'uzun',
  ],
  jizzax: [
    'jizzax_sh', 'arnasoy', 'baxmal', 'do_stlik',
    'forish', 'g_allaorol', 'sharof_rashidov',
    'mirzacho_l', 'paxtakor', 'yangiobod', 'zafarobod',
    'zarbdor', 'zomin',
  ],
  sirdaryo: [
    'guliston_sh', 'shirin_sh', 'yangiyer_sh', 'guliston_t',
    'boyovut', 'hovos', 'mirzaobod', 'oqoltin',
    'sardoba', 'sayxunobod', 'sirdaryo_t',
  ],
  navoiy: [
    'navoiy_sh', 'zarafshon_sh', 'g_ozg_on_sh', 'karmana',
    'konimex', 'navbahor', 'nurota', 'qiziltepa',
    'tomdi', 'uchquduq', 'xatirchi',
  ],
  xorazm: [
    'urganch_sh', 'xiva_sh', 'urganch_t', 'bog_ot',
    'gurlan', 'xazorasp', 'xiva_t', 'xonqa',
    'qo_shko_pir', 'shovot', 'yangiariq', 'yangibozor',
    'tuproqqala',
  ],
  qoraqalpogiston: [
    'nukus_sh', 'nukus_t', 'amudaryo', 'beruniy',
    'chimboy', 'ellikqala', 'kegeyli', 'moynaq',
    'qanliko_l', 'qo_ng_irot', 'qorao_zak', 'shumanay',
    'taxiatosh', 'taxtako_pir', 'to_rtko_l', 'xo_jayli',
    'bo_zatov',
  ],
};

export const REGION_KEYS = Object.keys(REGIONS);

export function getRegionOptions(t: TFunction) {
  const priorityKeys = ['toshkent_shahri', 'toshkent_viloyati'];
  const otherKeys = REGION_KEYS.filter((key) => !priorityKeys.includes(key));

  const priorityOptions = priorityKeys.map((key) => ({
    value: key,
    label: t(`locations.region.${key}`, { ns: 'common' }),
    breakAfter: key === 'toshkent_viloyati',
  }));

  const otherOptions = otherKeys.map((key) => ({
    value: key,
    label: t(`locations.region.${key}`, { ns: 'common' }),
  }));

  otherOptions.sort((a, b) => a.label.localeCompare(b.label, 'ru'));

  return [...priorityOptions, ...otherOptions];
}

export function getDistrictOptions(regionKey: string, t: TFunction) {
  const districts = REGIONS[regionKey];
  if (!districts) return [];

  const options = districts.map((key) => ({
    value: key,
    label: t(`locations.district.${key}`, { ns: 'common' }),
  }));

  const cities = options.filter((opt) => opt.label.startsWith('г.'));
  const regularDistricts = options.filter((opt) => !opt.label.startsWith('г.'));

  cities.sort((a, b) => a.label.localeCompare(b.label, 'ru'));
  regularDistricts.sort((a, b) => a.label.localeCompare(b.label, 'ru'));

  return [...cities, ...regularDistricts];
}

/** Reverse lookup: find which region a district belongs to */
export function findRegionByDistrict(districtKey: string): string | null {
  for (const [region, districts] of Object.entries(REGIONS)) {
    if (districts.includes(districtKey)) return region;
  }
  return null;
}
