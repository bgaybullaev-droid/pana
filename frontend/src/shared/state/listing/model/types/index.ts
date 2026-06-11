export interface ListingImageCreateData {
	original_url: string;
	thumbnail_url?: string;
	medium_url?: string;
	large_url?: string;
	position?: number;
	is_primary?: boolean;
}

export interface ListingCreateData {
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	title?: string;
	description?: string;
	/** Seller wishes forwarded into the AI prompt (pass-through, not stored). */
	ai_wishes?: string;
	price: number;
	currency: "USD" | "UZS";
	rooms?: number;
	area?: number;
	living_area?: number;
	kitchen_area?: number;
	land_area?: number;
	floor?: number;
	total_floors?: number;
	building_type?: string;
	condition?: string;
	house_type?: string;
	house_condition?: string[];
	location_type?: string[];
	water_supply?: string[];
	electricity?: string;
	heating?: string[];
	gas_supply?: string;
	sewage?: string;
	is_furnished?: boolean;
	is_negotiable?: boolean;
	land_purpose?: string;
	amenities?: string[];
	nearby_amenities?: string[];
	region?: string;
	district: string;
	address?: string;
	latitude?: number;
	longitude?: number;
	phone?: string;
	seller_type?: string;
	images?: ListingImageCreateData[];
	// Sprint 2 — rent group (T-002, T-003)
	// Loose string type — backend Pydantic pattern is the authoritative gate.
	rent_period?: string;
	deposit?: number;
	utilities_incl?: boolean;
	min_rent_months?: number;
	allowed_students?: boolean;
	allowed_pets?: boolean;
	rent_payment?: string[];
	// Sprint 2 — sale finance + deed (T-004, T-005)
	mortgage_ok?: boolean;
	installment_ok?: boolean;
	halol_ok?: boolean;
	deed_type?: string;
	// Sprint 3 (T-001) — cross-cutting location
	urgent_flag?: boolean;
	city?: string;
	microdistrict?: string;
	jk_name?: string;
	landmark?: string;
	metro_station?: string;
	seller_telegram?: string;
	// Sprint 4 (T-009) — commercial
	commercial_type?: string;
	price_per_sqm?: number;
	ceiling_height?: number;
	entrance?: string;
	parking_comm?: boolean;
	building_class?: string;
	// Sprint 5 (T-006, T-008) — dual-read renames. Submit `market_type` /
	// `furniture` on new writes; leave `building_type` / `is_furnished`
	// undefined or the backend will 400 with a dual-read conflict.
	market_type?: string;
	wall_material?: string;
	furniture?: string;
	// Sprint 6 (T-011, T-014, T-015) — property polish
	garage?: boolean;
	basement?: boolean;
	buildings_exist?: boolean;
	fence?: boolean;
	land_shape?: string;
	balcony?: string;
	listing_subtype?: string;
	floor_plan_url?: string;
	// Sprint 7 (T-027) — housing complex linkage
	jk_id?: string;
}

export interface ListingUpdateData extends Partial<ListingCreateData> {
	status?: "active" | "paused" | "sold";
}

export interface UploadImageResponse {
	original_url: string;
	thumbnail_url: string;
	medium_url: string;
	large_url: string;
	key: string;
}
