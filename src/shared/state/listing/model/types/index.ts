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
	floor?: number;
	total_floors?: number;
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
