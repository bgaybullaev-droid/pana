import { useState, useMemo, useEffect, useRef } from "react";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useTranslation } from "react-i18next";
import {
	uploadImageFx,
	type ListingImageCreateData,
} from "@shared/state/listing/model";
import {
	getRegionOptions,
	getDistrictOptions,
} from "@shared/constants/regions";
import { saveDraft } from "./listingDraftStorage";

export type ImageItem =
	| { kind: "uploaded"; data: ListingImageCreateData }
	| { kind: "pending"; file: File; previewUrl: string };

export interface ListingFormValues {
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	title: string;
	description: string;
	price: number | undefined;
	currency: "USD" | "UZS";
	is_negotiable: boolean;
	// Dimensions
	rooms: number | undefined;
	area: number | undefined;
	living_area: number | undefined;
	kitchen_area: number | undefined;
	land_area: number | undefined;
	floor: number | undefined;
	total_floors: number | undefined;
	// Apartment attributes
	building_type: string | undefined;
	condition: string | undefined;
	// House attributes
	house_type: string | undefined;
	house_condition: string[];
	location_type: string[];
	water_supply: string[];
	electricity: string | undefined;
	heating: string[];
	gas_supply: string | undefined;
	sewage: string | undefined;
	// Common attributes
	is_furnished: string | undefined;
	land_purpose: string | undefined;
	// Amenities
	amenities: string[];
	nearby_amenities: string[];
	// Sprint 2 — rent group (T-002, T-003)
	rent_period: string | undefined;
	deposit: number | undefined;
	utilities_incl: boolean | undefined;
	min_rent_months: number | undefined;
	allowed_students: boolean | undefined;
	allowed_pets: boolean | undefined;
	rent_payment: string[];
	// Sprint 2 — sale finance + deed (T-004, T-005)
	mortgage_ok: boolean;
	installment_ok: boolean;
	halol_ok: boolean;
	deed_type: string | undefined;
	// ── Sprint 3 (T-001) — cross-cutting location ──
	urgent_flag: boolean;
	microdistrict: string | undefined;
	jk_name: string | undefined;
	landmark: string | undefined;
	metro_station: string | undefined;
	seller_telegram: string | undefined;
	// ── Sprint 4 (T-009) — commercial ──
	commercial_type: string | undefined;
	price_per_sqm: number | undefined;
	ceiling_height: number | undefined;
	entrance: string | undefined;
	parking_comm: boolean | undefined;
	building_class: string | undefined;
	// ── Sprint 5 (T-006, T-008) — dual-read renames ──
	// New canonical columns. Legacy `building_type` / `is_furnished` kept
	// above for edit-mode pre-fill, never submitted on new writes.
	market_type: string | undefined;
	wall_material: string | undefined;
	furniture: string | undefined;
	// ── Sprint 6 (T-011, T-014, T-015) — property polish ──
	garage: boolean | undefined;
	basement: boolean | undefined;
	buildings_exist: boolean | undefined;
	fence: boolean | undefined;
	land_shape: string | undefined;
	balcony: string | undefined;
	listing_subtype: string | undefined;
	floor_plan_url: string | undefined;
	// ── Sprint 7 (T-027) — housing complex linkage ──
	jk_id: string | undefined;
	// Location
	region: string;
	district: string;
	address: string;
	latitude: number | undefined;
	longitude: number | undefined;
	// Contact
	phone: string;
	seller_type: string;
}

export type ListingFormMode = "create" | "edit";

export function useListingForm(
	mode: ListingFormMode = "create",
	initialOverrides?: Partial<ListingFormValues>,
	initialImages?: ListingImageCreateData[],
) {
	const { t } = useTranslation("seller");
	const [images, setImages] = useState<ImageItem[]>(() =>
		(initialImages ?? []).map(data => ({ kind: "uploaded" as const, data })),
	);
	const [uploadingCount, setUploadingCount] = useState(0);
	const isUploading = uploadingCount > 0;
	const [uploadProgress, setUploadProgress] = useState(0);

	const regions = getRegionOptions(t);

	const form = useForm<ListingFormValues>({
		initialValues: {
			type: "sell",
			property_type: "apartment",
			title: "",
			description: "",
			price: undefined,
			currency: "USD",
			is_negotiable: false,
			rooms: undefined,
			area: undefined,
			living_area: undefined,
			kitchen_area: undefined,
			land_area: undefined,
			floor: undefined,
			total_floors: undefined,
			building_type: undefined,
			condition: undefined,
			house_type: undefined,
			house_condition: [],
			location_type: [],
			water_supply: [],
			electricity: undefined,
			heating: [],
			gas_supply: undefined,
			sewage: undefined,
			is_furnished: undefined,
			land_purpose: undefined,
			amenities: [],
			nearby_amenities: [],
			// Sprint 2 — rent group
			rent_period: undefined,
			deposit: undefined,
			utilities_incl: undefined,
			min_rent_months: undefined,
			allowed_students: undefined,
			allowed_pets: undefined,
			rent_payment: [],
			// Sprint 2 — sale finance + deed
			mortgage_ok: false,
			installment_ok: false,
			halol_ok: false,
			deed_type: undefined,
			// Sprint 3 — cross-cutting location
			urgent_flag: false,
			microdistrict: undefined,
			jk_name: undefined,
			landmark: undefined,
			metro_station: undefined,
			seller_telegram: undefined,
			// Sprint 4 — commercial
			commercial_type: undefined,
			price_per_sqm: undefined,
			ceiling_height: undefined,
			entrance: undefined,
			parking_comm: undefined,
			building_class: undefined,
			// Sprint 5 — dual-read
			market_type: undefined,
			wall_material: undefined,
			furniture: undefined,
			// Sprint 6 — property polish
			garage: undefined,
			basement: undefined,
			buildings_exist: undefined,
			fence: undefined,
			land_shape: undefined,
			balcony: undefined,
			listing_subtype: undefined,
			floor_plan_url: undefined,
			// Sprint 7 — housing complex linkage
			jk_id: undefined,
			region: "",
			district: "",
			address: "",
			latitude: undefined,
			longitude: undefined,
			phone: "",
			seller_type: "",
			...(initialOverrides ?? {}),
		},
		validate: {
			type: (value, values) =>
				values.property_type !== "land" && !value
					? t("validation.dealTypeRequired")
					: null,
			price: (value, values) =>
				!values.is_negotiable && (!value || value <= 0)
					? t("validation.priceRequired")
					: null,
			rooms: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isHouse = values.property_type === "house";
				if ((isApt || isHouse) && value === undefined && values.listing_subtype !== "studio") {
					return t("validation.roomsRequired");
				}
				return null;
			},
			area: (value, values) => {
				if (values.property_type !== "land" && !value) {
					return t("validation.areaRequired");
				}
				return null;
			},
			floor: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				if ((isApt || isCom) && value === undefined) {
					return t("validation.floorRequired");
				}
				return null;
			},
			total_floors: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				const isHouse = values.property_type === "house";
				if ((isApt || isCom || isHouse) && value === undefined) {
					return t("validation.totalFloorsRequired");
				}
				return null;
			},
			// S5 dual-read: market_type replaces building_type as the required
			// apartment-only field. On edit, pre-fill maps the legacy column
			// to `market_type`, so this still passes for old listings.
			market_type: (value, values) =>
				values.property_type === "apartment" && !value
					? t("validation.buildingTypeRequired")
					: null,
			condition: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				if ((isApt || isCom) && !value) {
					return t("validation.conditionRequired");
				}
				return null;
			},
			// S5 dual-read: furniture replaces is_furnished. Required on
			// non-land listings. Edit-mode maps legacy boolean → enum.
			furniture: (value, values) =>
				values.property_type !== "land" && !value
					? t("validation.furnishedRequired")
					: null,
			// S4 (T-009): commercial listings require commercial_type on CREATE only.
			commercial_type: (value, values) =>
				mode === "create" && values.property_type === "commercial" && !value
					? t("validation.commercialTypeRequired")
					: null,
			// Sprint 2 — rent listings require a period (blueprint §3.3)
			rent_period: (value, values) =>
				values.type === "rent" && values.property_type !== "land" && !value
					? t("validation.rentPeriodRequired")
					: null,
			// Long-term rentals additionally require min_rent_months
			min_rent_months: (value, values) =>
				values.type === "rent" &&
				values.property_type !== "land" &&
				values.rent_period === "long_term" &&
				value === undefined
					? t("validation.minRentMonthsRequired")
					: null,
			region: (value) => (!value ? t("validation.regionRequired") : null),
			district: (value) => (!value ? t("validation.districtRequired") : null),
			latitude: (value) => (!value ? t("validation.mapRequired") : null),
		},
	});

	const districts = useMemo(
		() => getDistrictOptions(form.values.region, t),
		[form.values.region, t],
	);

	// Auto-save form values + uploaded images to localStorage (create mode, debounced 800 ms).
	const saveTimerRef = useRef<ReturnType<typeof setTimeout>>();
	useEffect(() => {
		if (mode !== "create") return;
		const uploadedImageData = images
			.filter((i): i is Extract<ImageItem, { kind: "uploaded" }> => i.kind === "uploaded")
			.map(i => i.data);
		clearTimeout(saveTimerRef.current);
		saveTimerRef.current = setTimeout(() => saveDraft(form.values, uploadedImageData), 800);
		return () => clearTimeout(saveTimerRef.current);
	// form.values and images are new references on each change — intentional deps.
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [form.values, images, mode]);

	const handleRegionChange = (value: string) => {
		form.setFieldValue("region", value);
		form.setFieldValue("district", "");
	};

	const handleAddImages = async (newFiles: File[]) => {
		const slots = 10 - images.length;
		if (slots <= 0) return;
		const files = newFiles.slice(0, slots);

		const pendingItems: ImageItem[] = files.map(f => ({
			kind: "pending" as const,
			file: f,
			previewUrl: URL.createObjectURL(f),
		}));

		setImages(prev => [...prev, ...pendingItems]);
		setUploadingCount(c => c + files.length);
		setUploadProgress(0);

		let doneCount = 0;
		for (const pendingItem of pendingItems) {
			if (pendingItem.kind !== "pending") continue;
			try {
				const result = await uploadImageFx(pendingItem.file);
				const uploadedItem: ImageItem = {
					kind: "uploaded",
					data: {
						original_url: result.original_url,
						thumbnail_url: result.thumbnail_url,
						medium_url: result.medium_url,
						large_url: result.large_url,
						position: 0,
						is_primary: false,
					},
				};
				setImages(prev => {
					const idx = prev.indexOf(pendingItem);
					if (idx === -1) return prev;
					const next = [...prev];
					next[idx] = uploadedItem;
					let pos = 0;
					return next.map(item =>
						item.kind === "uploaded"
							? { ...item, data: { ...item.data, position: pos++, is_primary: pos === 1 } }
							: item,
					);
				});
			} catch {
				setImages(prev => {
					const it = prev.find(i => i === pendingItem);
					if (it?.kind === "pending") URL.revokeObjectURL(it.previewUrl);
					return prev.filter(i => i !== pendingItem);
				});
				notifications.show({
					title: t("notifications.warning"),
					message: t("notifications.imageUploadFailed"),
					color: "yellow",
				});
			}
			doneCount++;
			setUploadingCount(c => c - 1);
			setUploadProgress(Math.round((doneCount / files.length) * 100));
		}
	};

	const handleRemoveImage = (index: number) => {
		setImages(prev => {
			const item = prev[index];
			if (item?.kind === "pending") URL.revokeObjectURL(item.previewUrl);
			return prev.filter((_, i) => i !== index);
		});
	};

	// Images are pre-uploaded via handleAddImages; just return the uploaded ones.
	const handleUploadImages = async (positionOffset = 0): Promise<ListingImageCreateData[]> => {
		return images
			.filter((i): i is Extract<ImageItem, { kind: "uploaded" }> => i.kind === "uploaded")
			.map((item, idx) => ({
				...item.data,
				position: positionOffset + idx,
				is_primary: positionOffset === 0 && idx === 0,
			}));
	};

	// Dual-read submit rule (Sprint 5 — T-006, T-008):
	// When both `building_type`/`market_type` or `is_furnished`/`furniture`
	// are on the wire, backend `_apply_dual_read_inputs` returns 400. We
	// submit ONLY the new names (`market_type`, `furniture`). If the user
	// edited an old listing, `market_type`/`furniture` are pre-filled from
	// the legacy column via the edit page — so the new name always carries
	// the authoritative value by submit time.
	const buildListingData = (values: ListingFormValues) => ({
		type: values.type,
		property_type: values.property_type,
		title: values.title || undefined,
		description: values.description || undefined,
		price: values.is_negotiable ? 0 : values.price!,
		currency: values.currency,
		is_negotiable: values.is_negotiable,
		rooms: values.listing_subtype === "studio" ? 0 : values.rooms,
		area: values.area,
		living_area: values.living_area,
		kitchen_area: values.kitchen_area,
		land_area: values.land_area,
		floor: values.floor,
		total_floors: values.total_floors,
		// Dual-read: do NOT submit `building_type` or `is_furnished`. They
		// are kept in form state only so edit-mode pre-fill of legacy
		// listings populates the new columns.
		condition: values.condition || undefined,
		house_type: values.house_type || undefined,
		house_condition:
			values.house_condition.length > 0 ? values.house_condition : undefined,
		location_type:
			values.location_type.length > 0 ? values.location_type : undefined,
		water_supply:
			values.water_supply.length > 0 ? values.water_supply : undefined,
		electricity: values.electricity || undefined,
		heating: values.heating.length > 0 ? values.heating : undefined,
		gas_supply: values.gas_supply || undefined,
		sewage: values.sewage || undefined,
		land_purpose: values.land_purpose || undefined,
		amenities: values.amenities.length > 0 ? values.amenities : undefined,
		nearby_amenities:
			values.nearby_amenities.length > 0 ? values.nearby_amenities : undefined,
		// Sprint 2 — rent group (matrix-gated by backend)
		rent_period: values.rent_period || undefined,
		deposit: values.deposit,
		utilities_incl: values.utilities_incl,
		min_rent_months: values.min_rent_months,
		allowed_students: values.allowed_students,
		allowed_pets: values.allowed_pets,
		rent_payment:
			values.rent_payment.length > 0 ? values.rent_payment : undefined,
		// Sprint 2 — sale finance + deed (matrix-gated by backend)
		mortgage_ok: values.mortgage_ok,
		installment_ok: values.installment_ok,
		halol_ok: values.halol_ok,
		deed_type: values.deed_type || undefined,
		// Sprint 3 — cross-cutting location (T-001)
		urgent_flag: values.urgent_flag,
		microdistrict: values.microdistrict || undefined,
		jk_name: values.jk_name || undefined,
		landmark: values.landmark || undefined,
		metro_station: values.metro_station || undefined,
		seller_telegram: values.seller_telegram || undefined,
		// Sprint 4 — commercial (T-009)
		commercial_type: values.commercial_type || undefined,
		price_per_sqm: values.price_per_sqm,
		ceiling_height: values.ceiling_height,
		entrance: values.entrance || undefined,
		parking_comm: values.parking_comm,
		building_class: values.building_class || undefined,
		// Sprint 5 — dual-read new columns (authoritative on submit)
		market_type: values.market_type || undefined,
		wall_material: values.wall_material || undefined,
		furniture: values.furniture || undefined,
		// Sprint 6 — property polish (T-011, T-014, T-015)
		garage: values.garage,
		basement: values.basement,
		buildings_exist: values.buildings_exist,
		fence: values.fence,
		land_shape: values.land_shape || undefined,
		balcony: values.balcony || undefined,
		listing_subtype: values.listing_subtype || undefined,
		floor_plan_url: values.floor_plan_url || undefined,
		// Sprint 7 — housing complex linkage (T-027)
		jk_id: values.jk_id || undefined,
		region: values.region,
		district: values.district,
		address: values.address || undefined,
		latitude: values.latitude,
		longitude: values.longitude,
		phone: values.phone || undefined,
		seller_type: values.seller_type || undefined,
	});

	return {
		form,
		images,
		isUploading,
		uploadProgress,
		regions,
		districts,
		handleRegionChange,
		handleAddImages,
		handleRemoveImage,
		handleUploadImages,
		buildListingData,
		t,
	};
}
