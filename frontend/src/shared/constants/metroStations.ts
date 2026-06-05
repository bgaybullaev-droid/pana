/**
 * Tashkent Metro stations registry — single source of truth for the
 * `metro_station` picker in the seller listing form.
 *
 * Only Tashkent has a metro, so the picker is gated to region
 * `toshkent_shahri` (P5 rule, enforced in ListingFormFields + backend
 * `_clear_incompatible_fields`). Stations are listed in line order; the
 * `line` field drives chip grouping today and district-scoped filtering
 * later. Coordinates are WGS-84 (lat/lng), used for map centring and for
 * assigning each station to a district once admin polygons are available.
 *
 * Source: all 49 currently-operating stations across four lines — Chilonzor,
 * Oʻzbekiston, Yunusobod and the elevated Ring (Halqa) line. Coordinates from
 * the open Tashkent-metro dataset (JamshidSod/tashkent-metro-accessibility).
 *
 * Each `key` doubles as the i18n label key: `createListing.metroStation.<key>`
 * (locales: ru, uz-latn, uz-cyrl; `uz` falls back to ru).
 */

export type MetroLine = "chilonzor" | "ozbekiston" | "yunusobod" | "ring";

export interface MetroStation {
	/** Stable key; also the i18n label key `createListing.metroStation.<key>`. */
	key: string;
	/** Line the station belongs to (used for ordering / grouping). */
	line: MetroLine;
	/** Tashkent-city district key (toshkent_shahri) the station sits in. */
	district: string;
	/** WGS-84 latitude. */
	lat: number;
	/** WGS-84 longitude. */
	lng: number;
}

// Listed in line order; within each line, in geographic sequence (the Ring
// line is ordered around the loop).
export const METRO_STATIONS: MetroStation[] = [
	// ── Chilonzor line (red) ──
	{ key: "buyuk_ipak_yoli", line: "chilonzor", district: "mirzo_ulugbek", lat: 41.3261054, lng: 69.3285598 },
	{ key: "pushkin", line: "chilonzor", district: "mirzo_ulugbek", lat: 41.3219481, lng: 69.311102 },
	{ key: "hamid_olimjon", line: "chilonzor", district: "mirzo_ulugbek", lat: 41.3181644, lng: 69.2957419 },
	{ key: "amir_temur_xiyoboni", line: "chilonzor", district: "mirzo_ulugbek", lat: 41.3126738, lng: 69.2832691 },
	{ key: "mustaqillik_maydoni", line: "chilonzor", district: "yunusobod", lat: 41.3149453, lng: 69.2710646 },
	{ key: "paxtakor", line: "chilonzor", district: "shayxontohur", lat: 41.3177914, lng: 69.2550882 },
	{ key: "xalqlar_dostligi", line: "chilonzor", district: "shayxontohur", lat: 41.3118987, lng: 69.2430959 },
	{ key: "milliy_bog", line: "chilonzor", district: "chilonzor", lat: 41.3033944, lng: 69.2356663 },
	{ key: "novza", line: "chilonzor", district: "chilonzor", lat: 41.2918722, lng: 69.2236165 },
	{ key: "mirzo_ulugbek", line: "chilonzor", district: "chilonzor", lat: 41.2820342, lng: 69.2125834 },
	{ key: "chilonzor", line: "chilonzor", district: "chilonzor", lat: 41.274359, lng: 69.2049735 },
	{ key: "olmazor", line: "chilonzor", district: "chilonzor", lat: 41.2566724, lng: 69.1961045 },
	{ key: "choshtepa", line: "chilonzor", district: "yangihayot", lat: 41.2382496, lng: 69.1960345 },
	{ key: "ozgarish", line: "chilonzor", district: "yangihayot", lat: 41.2273364, lng: 69.2039714 },
	{ key: "yangihayot", line: "chilonzor", district: "yangihayot", lat: 41.2135099, lng: 69.214015 },
	{ key: "chinor", line: "chilonzor", district: "yangihayot", lat: 41.2066965, lng: 69.2189575 },
	// ── Oʻzbekiston line (blue) ──
	{ key: "beruniy", line: "ozbekiston", district: "shayxontohur", lat: 41.3446152, lng: 69.2062046 },
	{ key: "tinchlik", line: "ozbekiston", district: "shayxontohur", lat: 41.3323014, lng: 69.2191155 },
	{ key: "chorsu", line: "ozbekiston", district: "shayxontohur", lat: 41.3258649, lng: 69.2368152 },
	{ key: "gafur_gulom", line: "ozbekiston", district: "olmazor", lat: 41.3278828, lng: 69.2458342 },
	{ key: "alisher_navoiy", line: "ozbekiston", district: "shayxontohur", lat: 41.3189218, lng: 69.2542973 },
	{ key: "ozbekiston", line: "ozbekiston", district: "shayxontohur", lat: 41.3119437, lng: 69.2534057 },
	{ key: "kosmonavtlar", line: "ozbekiston", district: "yakkasaroy", lat: 41.3051618, lng: 69.2647207 },
	{ key: "oybek", line: "ozbekiston", district: "mirobod", lat: 41.2980128, lng: 69.2740501 },
	{ key: "toshkent", line: "ozbekiston", district: "mirobod", lat: 41.2932886, lng: 69.2877212 },
	{ key: "mashinasozlar", line: "ozbekiston", district: "yashnobod", lat: 41.2989847, lng: 69.3051276 },
	{ key: "dostlik", line: "ozbekiston", district: "yashnobod", lat: 41.2936401, lng: 69.3222445 },
	// ── Yunusobod line (green) ──
	{ key: "turkiston", line: "yunusobod", district: "yunusobod", lat: 41.3775217, lng: 69.2960151 },
	{ key: "yunusobod", line: "yunusobod", district: "yunusobod", lat: 41.3668411, lng: 69.2923003 },
	{ key: "shahriston", line: "yunusobod", district: "yunusobod", lat: 41.3531185, lng: 69.2881069 },
	{ key: "bodomzor", line: "yunusobod", district: "yunusobod", lat: 41.3371701, lng: 69.2845697 },
	{ key: "minor", line: "yunusobod", district: "yunusobod", lat: 41.3268923, lng: 69.2834163 },
	{ key: "abdulla_qodiriy", line: "yunusobod", district: "yunusobod", lat: 41.3201924, lng: 69.281759 },
	{ key: "yunus_rajabiy", line: "yunusobod", district: "mirzo_ulugbek", lat: 41.3138871, lng: 69.2835077 },
	{ key: "ming_urik", line: "yunusobod", district: "mirobod", lat: 41.299661, lng: 69.2744102 },
	// ── Ring line (Halqa) ──
	{ key: "tolarik", line: "ring", district: "sergeli", lat: 41.2445139, lng: 69.2849568 },
	{ key: "qipchok", line: "ring", district: "yangihayot", lat: 41.2054229, lng: 69.2214112 },
	{ key: "turon", line: "ring", district: "yangihayot", lat: 41.2106813, lng: 69.234154 },
	{ key: "xonobod", line: "ring", district: "sergeli", lat: 41.2300103, lng: 69.2704353 },
	{ key: "quruvchilar", line: "ring", district: "sergeli", lat: 41.2216367, lng: 69.2605033 },
	{ key: "qiyot", line: "ring", district: "sergeli", lat: 41.2444796, lng: 69.299728 },
	{ key: "matonat", line: "ring", district: "mirobod", lat: 41.2444713, lng: 69.3083229 },
	{ key: "qoyliq", line: "ring", district: "bektemir", lat: 41.2374579, lng: 69.3270001 },
	{ key: "yangiobod", line: "ring", district: "yashnobod", lat: 41.2565075, lng: 69.3587242 },
	{ key: "rohat", line: "ring", district: "yashnobod", lat: 41.2652907, lng: 69.3647517 },
	{ key: "olmos", line: "ring", district: "yashnobod", lat: 41.281705, lng: 69.3603338 },
	{ key: "tuzel", line: "ring", district: "yashnobod", lat: 41.2920125, lng: 69.3561844 },
	{ key: "yashnobod", line: "ring", district: "yashnobod", lat: 41.2975859, lng: 69.3497831 },
	{ key: "texnopark", line: "ring", district: "yashnobod", lat: 41.294628, lng: 69.3231867 },
];
