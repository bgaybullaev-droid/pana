/**
 * Approximate center coordinates for Uzbekistan regions and districts.
 * Used to sync map position when user selects region/district in forms.
 */

// [latitude, longitude, zoom]
type LocationEntry = [number, number, number];

const REGION_COORDS: Record<string, LocationEntry> = {
	toshkent_shahri: [41.311, 69.279, 12],
	toshkent_viloyati: [41.311, 69.279, 10],
	samarqand: [39.654, 66.959, 11],
	buxoro: [39.774, 64.421, 11],
	andijon: [40.783, 72.344, 11],
	fargona: [40.384, 71.789, 11],
	namangan: [41.0, 71.672, 11],
	qashqadaryo: [38.86, 65.8, 10],
	surxondaryo: [37.224, 67.278, 10],
	jizzax: [40.119, 67.842, 10],
	sirdaryo: [40.838, 68.665, 10],
	navoiy: [40.103, 65.379, 10],
	xorazm: [41.553, 60.631, 11],
	qoraqalpogiston: [42.461, 59.6, 9],
};

const DISTRICT_COORDS: Record<string, LocationEntry> = {
	// Tashkent city
	bektemir: [41.212, 69.326, 14],
	chilonzor: [41.262, 69.187, 14],
	mirzo_ulugbek: [41.352, 69.335, 14],
	mirobod: [41.306, 69.274, 14],
	olmazor: [41.337, 69.222, 14],
	sergeli: [41.21, 69.232, 14],
	shayxontohur: [41.332, 69.243, 14],
	uchtepa: [41.312, 69.192, 14],
	yakkasaroy: [41.291, 69.266, 14],
	yashnobod: [41.288, 69.331, 14],
	yunusobod: [41.37, 69.279, 14],
	// Tashkent region cities
	nurafshon: [41.064, 69.232, 13],
	olmaliq: [40.844, 69.599, 13],
	angren: [41.017, 70.144, 13],
	bekobod: [40.221, 69.269, 13],
	chirchiq: [41.469, 69.582, 13],
	// Samarkand
	samarqand_sh: [39.654, 66.959, 14],
	// Bukhara
	buxoro_sh: [39.774, 64.421, 14],
	// Andijan
	andijon_sh: [40.783, 72.344, 14],
	// Fergana
	fargona_sh: [40.384, 71.789, 14],
	marg_ilon: [40.467, 71.724, 14],
	quvasoy: [40.31, 71.978, 14],
	// Namangan
	namangan_sh: [41.0, 71.672, 14],
	// Kashkadarya
	qarshi_sh: [38.86, 65.8, 14],
	shahrisabz: [39.055, 66.83, 14],
	// Surkhandarya
	termiz_sh: [37.224, 67.278, 14],
	// Jizzakh
	jizzax_sh: [40.119, 67.842, 14],
	// Syrdarya
	guliston_sh: [40.488, 68.784, 14],
	// Navoi
	navoiy_sh: [40.103, 65.379, 14],
	// Khorezm
	urganch_sh: [41.553, 60.631, 14],
	xiva: [41.378, 60.364, 14],
	// Karakalpakstan
	nukus_sh: [42.461, 59.6, 14],
};

/**
 * Resolve coordinates for a region or district key.
 * Returns [lat, lng, zoom] or null.
 */
export function resolveLocationCoords(
	region: string | null | undefined,
	district: string | null | undefined,
): { lat: number; lng: number; zoom: number } | null {
	// Prioritize district (most specific)
	if (district) {
		const d = DISTRICT_COORDS[district];
		if (d) return { lat: d[0], lng: d[1], zoom: d[2] };
	}
	// Fall back to region
	if (region) {
		const r = REGION_COORDS[region];
		if (r) return { lat: r[0], lng: r[1], zoom: r[2] };
	}
	return null;
}
