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
