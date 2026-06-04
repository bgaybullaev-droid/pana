import type { ListingCreateData } from "@shared/state/listing/model";
import type { ListingFormValues } from "./useListingForm";

const DRAFT_KEY = "listing_draft_stage1_v1";
const EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 h

export function saveDraft(values: ListingFormValues): void {
	try {
		localStorage.setItem(DRAFT_KEY, JSON.stringify({ values, savedAt: Date.now() }));
	} catch {
		// Ignore quota errors
	}
}

export function loadDraft(): Partial<ListingFormValues> | null {
	try {
		const raw = localStorage.getItem(DRAFT_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as { values: ListingFormValues; savedAt: number };
		if (Date.now() - parsed.savedAt > EXPIRY_MS) {
			clearDraft();
			return null;
		}
		return parsed.values;
	} catch {
		return null;
	}
}

export function clearDraft(): void {
	localStorage.removeItem(DRAFT_KEY);
}

/** Map ListingCreateData → Partial<ListingFormValues> for Stage2 → Stage1 back-navigation pre-fill. */
export function draftDataToFormValues(data: ListingCreateData): Partial<ListingFormValues> {
	return {
		type: data.type,
		property_type: data.property_type,
		title: data.title ?? "",
		description: data.description ?? "",
		price: data.price,
		currency: data.currency,
		is_negotiable: data.is_negotiable ?? false,
		rooms: data.rooms,
		area: data.area,
		living_area: data.living_area,
		kitchen_area: data.kitchen_area,
		land_area: data.land_area,
		floor: data.floor,
		total_floors: data.total_floors,
		condition: data.condition,
		house_type: data.house_type,
		house_condition: data.house_condition ?? [],
		location_type: data.location_type ?? [],
		water_supply: data.water_supply ?? [],
		electricity: data.electricity,
		heating: data.heating ?? [],
		gas_supply: data.gas_supply,
		sewage: data.sewage,
		land_purpose: data.land_purpose,
		amenities: data.amenities ?? [],
		nearby_amenities: data.nearby_amenities ?? [],
		rent_period: data.rent_period,
		deposit: data.deposit,
		utilities_incl: data.utilities_incl,
		min_rent_months: data.min_rent_months,
		allowed_students: data.allowed_students,
		allowed_pets: data.allowed_pets,
		rent_payment: data.rent_payment ?? [],
		mortgage_ok: data.mortgage_ok ?? false,
		installment_ok: data.installment_ok ?? false,
		halol_ok: data.halol_ok ?? false,
		deed_type: data.deed_type,
		urgent_flag: data.urgent_flag ?? false,
		microdistrict: data.microdistrict,
		jk_name: data.jk_name,
		landmark: data.landmark,
		metro_station: data.metro_station,
		seller_telegram: data.seller_telegram,
		commercial_type: data.commercial_type,
		price_per_sqm: data.price_per_sqm,
		ceiling_height: data.ceiling_height,
		entrance: data.entrance,
		parking_comm: data.parking_comm,
		building_class: data.building_class,
		market_type: data.market_type,
		wall_material: data.wall_material,
		furniture: data.furniture,
		garage: data.garage,
		basement: data.basement,
		buildings_exist: data.buildings_exist,
		fence: data.fence,
		land_shape: data.land_shape,
		balcony: data.balcony,
		listing_subtype: data.listing_subtype,
		floor_plan_url: data.floor_plan_url,
		jk_id: data.jk_id,
		region: data.region ?? "",
		district: data.district ?? "",
		address: data.address ?? "",
		latitude: data.latitude,
		longitude: data.longitude,
		phone: data.phone ?? "",
		seller_type: data.seller_type ?? "",
	};
}
