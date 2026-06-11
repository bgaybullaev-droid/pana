import type React from "react";
import {
	ActionIcon,
	Anchor,
	Textarea,
	NumberInput,
	Box,
	Group,
	Loader,
	Skeleton,
	Text,
	Switch,
	TextInput,
	Select,
} from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { FormSection } from "@shared/ui/FormSection";
import { ChipSelect } from "@shared/ui/ChipSelect";
import { ChipMultiSelect } from "@shared/ui/ChipMultiSelect";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { HousingComplexAutocomplete } from "@shared/ui/HousingComplexAutocomplete";
import { LandmarkAutocomplete } from "@shared/ui/LandmarkAutocomplete";
import { MicrodistrictAutocomplete } from "@shared/ui/MicrodistrictAutocomplete";
import { MetroStationAutocomplete } from "@shared/ui/MetroStationAutocomplete";
import { resolveLocationCoords } from "@shared/constants/locationCoords";
import { METRO_STATIONS } from "@shared/constants/metroStations";
import { apiClient } from "@shared/api/client";
import type { UseFormReturnType } from "@mantine/form";
import type { ListingFormValues } from "./useListingForm";
import {
	clearIncompatibleFields,
	isVisible,
	normalizeCombo,
} from "../lib/visibility";
import type { DealType, PropertyType } from "../lib/visibility";
import type { SectionKey, SectionState } from "../lib/requiredness";

// P5 sub-gate (blueprint §2.2): metro_station is only meaningful inside
// Tashkent. Mirrors backend `_clear_incompatible_fields` rule P5.
const TASHKENT_REGION = "toshkent_shahri";

// Sentinel value for the «+ Добавить контакт» action row appended to the
// verified-phones dropdown — picking it navigates instead of selecting.
const ADD_CONTACT_OPTION = "__add_contact__";

const MapPicker = lazy(() =>
	import("@shared/ui/MapPicker").then((m) => ({ default: m.MapPicker })),
);

interface ListingFormFieldsProps {
	form: UseFormReturnType<ListingFormValues>;
	regions: { value: string; label: string }[];
	districts: { value: string; label: string }[];
	onRegionChange: (value: string) => void;
	sectionBg?: string;
	beforeDescriptionContent?: React.ReactNode;
	afterDescriptionContent?: React.ReactNode;
	descriptionValueOverride?: string;
	onDescriptionChangeOverride?: (val: string) => void;
	/** AI generation in flight — skeleton overlay on the description field. */
	descriptionLoading?: boolean;
	/** Per-section completeness (useListingCompleteness). Omit → render as before. */
	sectionStates?: Record<SectionKey, SectionState>;
}

export function ListingFormFields({
	form,
	regions,
	districts,
	onRegionChange,
	sectionBg,
	beforeDescriptionContent,
	afterDescriptionContent,
	descriptionValueOverride,
	onDescriptionChangeOverride,
	descriptionLoading,
	sectionStates,
}: ListingFormFieldsProps) {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();
	const pt = form.values.property_type;
	const dt = form.values.type;

	// Per-field visibility resolved through the central matrix (T-031).
	// `marketType` / `furniture` are the Sprint-5 dual-read canonical names;
	// we gate on the new names and hide the legacy `building_type` /
	// `is_furnished` controls entirely. Pre-fill on edit maps old → new so
	// the legacy column stays in sync through `buildListingData`.
	const show = useMemo(
		() => ({
			rooms: isVisible("rooms", pt, dt),
			area: isVisible("area", pt, dt),
			livingArea: isVisible("living_area", pt, dt),
			kitchenArea: isVisible("kitchen_area", pt, dt),
			landArea: isVisible("land_area", pt, dt),
			floor: isVisible("floor", pt, dt),
			totalFloors: isVisible("total_floors", pt, dt),
			// S5: canonical names
			marketType: isVisible("market_type", pt, dt),
			wallMaterial: isVisible("wall_material", pt, dt),
			furniture: isVisible("furniture", pt, dt),
			condition: isVisible("condition", pt, dt),
			houseType: isVisible("house_type", pt, dt),
			utilities: isVisible("water_supply", pt, dt),
			aptAmenities: isVisible("amenities", pt, dt) && pt === "apartment",
			houseAmenities: isVisible("amenities", pt, dt) && pt === "house",
			nearbyAmenities: isVisible("nearby_amenities", pt, dt),
			landPurpose: isVisible("land_purpose", pt, dt),
			// S3 — matrix-gated location fields (always-visible ones handled
			// unconditionally in the Location section)
			jkName: isVisible("jk_name", pt, dt),
			metroStation:
				isVisible("metro_station", pt, dt) &&
				form.values.region === TASHKENT_REGION, // P5 region sub-gate
			// S4 — commercial (all matrix-gated to commercial)
			commercialType: isVisible("commercial_type", pt, dt),
			// ceilingHeight is now shown for apartment/house/commercial (not land)
			ceilingHeight: isVisible("ceiling_height", pt, dt),
			entrance: isVisible("entrance", pt, dt),
			parkingComm: isVisible("parking_comm", pt, dt),
			buildingClass: isVisible("building_class", pt, dt),
			// S6 — property polish
			garage: isVisible("garage", pt, dt),
			basement: isVisible("basement", pt, dt),
			buildingsExist: isVisible("buildings_exist", pt, dt),
			fence: isVisible("fence", pt, dt),
			landShape: isVisible("land_shape", pt, dt),
			balcony: isVisible("balcony", pt, dt),
			listingSubtype: isVisible("listing_subtype", pt, dt),
			// Floor plan is parked until a later product stage — to bring it
			// back replace `false` with isVisible("floor_plan_url", pt, dt).
			floorPlanUrl: false as boolean,
			// S2 — rent group (matrix-gated to rent × non-land). Required by
			// both frontend validation and backend publish.
			// Land rents long-term only (no daily land rentals on the market):
			// the selector is hidden and applyTransition pins long_term.
			rentPeriod: isVisible("rent_period", pt, dt) && pt !== "land",
			minRentMonths: isVisible("min_rent_months", pt, dt),
		}),
		// form.values.region feeds P5 region sub-gate for metro_station.
		[pt, dt, form.values.region],
	);

	const locationCenter = useMemo(
		() =>
			resolveLocationCoords(
				form.values.region || null,
				form.values.district || null,
			),
		[form.values.region, form.values.district],
	);

	// Location cascade: microdistrict / landmark / housing complex only
	// appear once a district is picked (or right after the region when the
	// region has no district list to offer).
	const districtChosen =
		!!form.values.district ||
		(!!form.values.region && districts.length === 0);

	// Block C V2.0 (C4) — verified-phones picker. Lists every phone the
	// seller has confirmed on /seller/phones; selecting one writes it back
	// to ``form.values.phone`` so the existing wire format (phone string)
	// is preserved. If the seller has only one phone (primary), the field
	// is hidden — defaulting silently keeps Stage 1 short. The freeform
	// PhoneInput remains as a manual fallback.
	const [verifiedPhones, setVerifiedPhones] = useState<
		Array<{ id: string; phone: string; is_primary: boolean }>
	>([]);
	useEffect(() => {
		let cancelled = false;
		apiClient
			.get<Array<{ id: string; phone: string; is_primary: boolean }>>(
				"/sellers/me/phones",
			)
			.then((res) => {
				if (cancelled) return;
				setVerifiedPhones(res.data || []);
				// Auto-seed the form phone with the primary one if blank — this
				// matches the previous silent-default behaviour but now explicit.
				if (!form.values.phone) {
					const primary =
						res.data?.find((p) => p.is_primary) ?? res.data?.[0];
					if (primary) {
						form.setFieldValue("phone", primary.phone);
					}
				}
			})
			.catch(() => {
				/* not a seller yet or offline — silent */
			});
		return () => {
			cancelled = true;
		};
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	// ── Option definitions ──

	const roomOpts = [
		{ value: "1", label: "1" },
		{ value: "2", label: "2" },
		{ value: "3", label: "3" },
		{ value: "4", label: "4" },
		{ value: "5", label: "5" },
		{ value: "6", label: "6" },
		{ value: "7", label: "7" },
		{ value: "8", label: "8" },
	];

	const areaOpts = [
		{ value: "30", label: "30 m²" },
		{ value: "40", label: "40 m²" },
		{ value: "50", label: "50 m²" },
		{ value: "60", label: "60 m²" },
		{ value: "80", label: "80 m²" },
		{ value: "100", label: "100 m²" },
		{ value: "150", label: "150 m²" },
		{ value: "200", label: "200 m²" },
	];

	const livingAreaOpts = [
		{ value: "20", label: "20 m²" },
		{ value: "30", label: "30 m²" },
		{ value: "40", label: "40 m²" },
		{ value: "50", label: "50 m²" },
		{ value: "60", label: "60 m²" },
		{ value: "80", label: "80 m²" },
		{ value: "100", label: "100 m²" },
	];

	const kitchenAreaOpts = [
		{ value: "5", label: "5 m²" },
		{ value: "7", label: "7 m²" },
		{ value: "9", label: "9 m²" },
		{ value: "12", label: "12 m²" },
		{ value: "15", label: "15 m²" },
		{ value: "20", label: "20 m²" },
	];

	const landAreaOpts = [
		{ value: "1", label: "1" },
		{ value: "2", label: "2" },
		{ value: "3", label: "3" },
		{ value: "4", label: "4" },
		{ value: "6", label: "6" },
		{ value: "8", label: "8" },
		{ value: "10", label: "10" },
		{ value: "15", label: "15" },
		{ value: "20", label: "20" },
	];

	const floorOpts = [
		{ value: "1", label: "1" },
		{ value: "2", label: "2" },
		{ value: "3", label: "3" },
		{ value: "4", label: "4" },
		{ value: "5", label: "5" },
		{ value: "6", label: "6" },
		{ value: "7", label: "7" },
		{ value: "8", label: "8" },
		{ value: "9", label: "9" },
	];

	const totalFloorsOpts = [
		{ value: "2", label: "2" },
		{ value: "4", label: "4" },
		{ value: "5", label: "5" },
		{ value: "9", label: "9" },
		{ value: "12", label: "12" },
		{ value: "16", label: "16" },
		{ value: "20", label: "20" },
	];

	const ceilingHeightOpts = [
		{ value: "2.5", label: "2.5 м" },
		{ value: "2.7", label: "2.7 м" },
		{ value: "3", label: "3 м" },
		{ value: "3.5", label: "3.5 м" },
		{ value: "4", label: "4 м" },
	];

	// House-specific options
	const houseTypeOpts = [
		{ value: "private_house", label: t("createListing.htPrivate") },
		{ value: "cottage", label: t("createListing.htCottage") },
		{ value: "townhouse", label: t("createListing.htTownhouse") },
		{ value: "country_house", label: t("createListing.htCountry") },
		{ value: "dacha", label: t("createListing.htDacha") },
		{ value: "part_of_house", label: t("createListing.htPart") },
	];

	const houseConditionOpts = [
		{ value: "designer", label: t("createListing.hcDesigner") },
		{ value: "medium_repair", label: t("createListing.hcMedium") },
		{ value: "euro", label: t("createListing.hcEuro") },
		{ value: "needs_repair", label: t("createListing.hcRepair") },
		{ value: "pre_finish", label: t("createListing.hcPreFinish") },
		{ value: "unfinished", label: t("createListing.hcUnfinished") },
		{ value: "rough", label: t("createListing.hcRough") },
		{ value: "demolish", label: t("createListing.hcDemolish") },
	];

	const locationTypeOpts = [
		{ value: "city", label: t("createListing.locCity") },
		{ value: "suburb", label: t("createListing.locSuburb") },
		{ value: "rural", label: t("createListing.locRural") },
		{ value: "highway", label: t("createListing.locHighway") },
		{ value: "waterfront", label: t("createListing.locWater") },
		{ value: "foothills", label: t("createListing.locFoothills") },
		{ value: "dacha_area", label: t("createListing.locDacha") },
		{ value: "gated", label: t("createListing.locGated") },
	];

	const waterSupplyOpts = [
		{ value: "in_house", label: t("createListing.wsInHouse") },
		{ value: "central", label: t("createListing.wsCentral") },
		{ value: "possible", label: t("createListing.wsPossible") },
		{ value: "well", label: t("createListing.wsWell") },
		{ value: "border", label: t("createListing.wsBorder") },
		{ value: "borehole", label: t("createListing.wsBorehole") },
		{ value: "none", label: t("createListing.wsNone") },
	];

	const heatingOpts = [
		{ value: "central", label: t("createListing.heatCentral") },
		{ value: "gas", label: t("createListing.heatGas") },
		{ value: "solid_fuel", label: t("createListing.heatSolid") },
		{ value: "liquid_fuel", label: t("createListing.heatLiquid") },
		{ value: "electric", label: t("createListing.heatElectric") },
		{ value: "mixed", label: t("createListing.heatMixed") },
		{ value: "none", label: t("createListing.heatNone") },
	];

	const yesNoPossibleOpts = [
		{ value: "yes", label: t("createListing.yes") },
		{ value: "no", label: t("createListing.no") },
		{ value: "possible", label: t("createListing.possible") },
	];

	const sewageOpts = [
		{ value: "central", label: t("createListing.sewCentral") },
		{ value: "septic", label: t("createListing.sewSeptic") },
		{ value: "none", label: t("createListing.sewNone") },
	];

	// Apartment condition
	// S4 (T-007): widened condition enum — matches backend DB CHECK.
	const conditionOpts = [
		{ value: "euro", label: t("createListing.condEuro") },
		{ value: "cosmetic", label: t("createListing.condCosmetic") },
		{ value: "needs_repair", label: t("createListing.condRepair") },
		{ value: "rough", label: t("createListing.condRough") },
		{ value: "none", label: t("createListing.condNone") },
		{ value: "shell", label: t("createListing.condShell") },
		{ value: "medium", label: t("createListing.condMedium") },
		{ value: "designer", label: t("createListing.condDesigner") },
		{ value: "turnkey", label: t("createListing.condTurnkey") },
		{
			value: "needs_repair_comm",
			label: t("createListing.condNeedsRepairComm"),
		},
	];

	// S5 (T-008): furniture replaces legacy is_furnished boolean.
	const furnitureOpts = [
		{ value: "none", label: t("createListing.furnitureNone") },
		{ value: "partial", label: t("createListing.furniturePartial") },
		{ value: "full", label: t("createListing.furnitureFull") },
		{ value: "built_in", label: t("createListing.furnitureBuiltIn") },
	];

	// S5 (T-006): market_type replaces legacy building_type. Values match
	// the old ones (new / secondary) so edit-mode pre-fill carries over.
	const marketTypeOpts = [
		{ value: "new", label: t("createListing.marketTypeNew") },
		{ value: "secondary", label: t("createListing.marketTypeSecondary") },
	];

	// S5 — wall_material (apartment + house)
	const wallMaterialOpts = [
		{ value: "brick", label: t("createListing.wallMaterialBrick") },
		{ value: "gasblock", label: t("createListing.wallMaterialGasblock") },
		{ value: "panel", label: t("createListing.wallMaterialPanel") },
		{ value: "monolith", label: t("createListing.wallMaterialMonolith") },
		{ value: "other", label: t("createListing.wallMaterialOther") },
	];

	// S4 — commercial enums
	const commercialTypeOpts = [
		{ value: "office", label: t("createListing.commercialTypeOffice") },
		{ value: "shop", label: t("createListing.commercialTypeShop") },
		{ value: "warehouse", label: t("createListing.commercialTypeWarehouse") },
		{ value: "production", label: t("createListing.commercialTypeProduction") },
		{ value: "restaurant", label: t("createListing.commercialTypeRestaurant") },
		{ value: "hotel", label: t("createListing.commercialTypeHotel") },
		{ value: "other", label: t("createListing.commercialTypeOther") },
	];

	const entranceOpts = [
		{ value: "separate", label: t("createListing.entranceSeparate") },
		{ value: "yard", label: t("createListing.entranceYard") },
		{ value: "street", label: t("createListing.entranceStreet") },
		{ value: "mall", label: t("createListing.entranceMall") },
	];

	const buildingClassOpts = [
		{ value: "standalone", label: t("createListing.buildingClassStandalone") },
		{ value: "embedded", label: t("createListing.buildingClassEmbedded") },
		{
			value: "business_center",
			label: t("createListing.buildingClassBusinessCenter"),
		},
		{ value: "mall", label: t("createListing.buildingClassMall") },
	];

	// S6 — property polish enums
	const balconyOpts = [
		{ value: "none", label: t("createListing.balconyNone") },
		{ value: "balcony", label: t("createListing.balconyBalcony") },
		{ value: "loggia", label: t("createListing.balconyLoggia") },
		{ value: "terrace", label: t("createListing.balconyTerrace") },
	];

	const listingSubtypeOpts = [
		{ value: "standard", label: t("createListing.listingSubtypeStandard") },
		{ value: "studio", label: t("createListing.listingSubtypeStudio") },
		{ value: "free_plan", label: t("createListing.listingSubtypeFreePlan") },
	];

	const landShapeOpts = [
		{ value: "rectangular", label: t("createListing.landShapeRectangular") },
		{ value: "irregular", label: t("createListing.landShapeIrregular") },
	];

	// S3 — metro stations of Tashkent (gated by P5 to region=toshkent_shahri).
	// Cascade: once a Tashkent district is chosen, only that district's
	// stations are offered (район → метро). Before a district is picked the
	// full list is shown. Chips wrap to a new row at each line boundary so
	// the lines read as visually distinct groups.
	// Show metro autocomplete only for Tashkent + after a district is selected
	// that actually has metro stations.
	const metroDistrict =
		form.values.region === TASHKENT_REGION && form.values.district
			? form.values.district
			: undefined;
	const metroDistrictHasStations = metroDistrict
		? METRO_STATIONS.some((s) => s.district === metroDistrict)
		: false;

	// Apartment amenities
	const aptAmenityOpts = [
		{ value: "internet", label: t("createListing.amenInternet") },
		{ value: "phone", label: t("createListing.amenPhone") },
		{ value: "fridge", label: t("createListing.amenFridge") },
		{ value: "tv", label: t("createListing.amenTv") },
		{ value: "ac", label: t("createListing.amenAc") },
		{ value: "cable_tv", label: t("createListing.amenCable") },
		{ value: "washing_machine", label: t("createListing.amenWashing") },
		{ value: "kitchen_set", label: t("createListing.amenKitchen") },
	];

	// House amenities (different set)
	const houseAmenityOpts = [
		{ value: "internet", label: t("createListing.amenInternet") },
		{ value: "phone", label: t("createListing.amenPhone") },
		{ value: "pool", label: t("createListing.amenPool") },
		{ value: "garage", label: t("createListing.amenGarage") },
		{ value: "ac", label: t("createListing.amenAc") },
		{ value: "appliances", label: t("createListing.amenAppliances") },
		{ value: "sewage", label: t("createListing.amenSewage") },
		{ value: "garden", label: t("createListing.amenGarden") },
		{ value: "security", label: t("createListing.amenSecurity") },
		{ value: "basement", label: t("createListing.amenBasement") },
		{ value: "sauna", label: t("createListing.amenSauna") },
		{ value: "gym", label: t("createListing.amenGym") },
		{ value: "satellite_tv", label: t("createListing.amenSatellite") },
	];

	const nearbyOpts = [
		{ value: "hospital", label: t("createListing.nearHospital") },
		{ value: "playground", label: t("createListing.nearPlayground") },
		{ value: "kindergarten", label: t("createListing.nearKindergarten") },
		{ value: "bus_stop", label: t("createListing.nearBus") },
		{ value: "park", label: t("createListing.nearPark") },
		{ value: "entertainment", label: t("createListing.nearEntertainment") },
		{ value: "restaurant", label: t("createListing.nearRestaurant") },
		{ value: "parking", label: t("createListing.nearParking") },
		{ value: "supermarket", label: t("createListing.nearSupermarket") },
		{ value: "school", label: t("createListing.nearSchool") },
	];

	// S6 (T-013): widened / re-coded enum — matches backend DB CHECK
	// (construction | commercial_land | agricultural | garden | unspecified).
	// Legacy values (`private`, `industrial`, `commercial`) were backfilled
	// by migration 20260419_s6_property_polish.py and are no longer valid
	// for new submits.
	// Deal-aware: renting land is about use (agriculture, dacha, commercial
	// use — parking/storage/trade), not construction, so the rent list drops
	// «под жилое строительство» and relabels commercial_land accordingly.
	// Same enum values either way — backend stays untouched.
	const landPurposeOpts =
		dt === "rent"
			? [
					{ value: "agricultural", label: t("createListing.lpAgricultural") },
					{ value: "garden", label: t("createListing.lpGarden") },
					{
						value: "commercial_land",
						label: t("createListing.lpCommercialUse"),
					},
					{ value: "unspecified", label: t("createListing.lpUnspecified") },
				]
			: [
					{ value: "construction", label: t("createListing.lpConstruction") },
					{ value: "garden", label: t("createListing.lpGarden") },
					{ value: "agricultural", label: t("createListing.lpAgricultural") },
					{
						value: "commercial_land",
						label: t("createListing.lpCommercialLand"),
					},
					{ value: "unspecified", label: t("createListing.lpUnspecified") },
				];

	const currencyOpts = [
		{ value: "USD", label: t("createListing.currencyUSD") },
		{ value: "UZS", label: t("createListing.currencyUZS") },
	];

	// Rent prices are period-priced (industry pattern: Avito/Cian always
	// name the period in the label). Daily wording differs: «за сутки» is
	// housing vocabulary, commercial days are «за день».
	const priceLabel =
		dt === "rent"
			? form.values.rent_period === "daily"
				? pt === "commercial"
					? t("createListing.rentPriceDayCommercialLabel")
					: t("createListing.rentPriceDayLabel")
				: form.values.rent_period === "long_term"
					? t("createListing.rentPriceMonthLabel")
					: t("createListing.rentPriceLabel")
			: t("createListing.priceLabel");

	const set = (key: string, val: any) => form.setFieldValue(key, val);

	// Same dimmed "необязательно" hint ChipSelect/ChipMultiSelect render on
	// their own, for the non-chip optional inputs (NumberInput, TextInput,
	// autocompletes) so every optional field in the form is marked alike.
	const optionalLabel = (label: string) => (
		<>
			{label}
			<Text span c="dimmed" fw={400} size="xs">
				{" "}
				— {t("createListing.optionalHint")}
			</Text>
		</>
	);

	// FormSection status props from the page-computed completeness map.
	// When `sectionStates` is absent (no page adopted it) sections render
	// exactly as before. `neutral` still passes `status` so the transparent
	// border reserves layout and complete/error transitions don't shift.
	const sectionStatusProps = (key: SectionKey) => {
		const state = sectionStates?.[key];
		if (!state) return {};
		if (state.status === "complete") {
			return {
				status: "complete" as const,
				statusLabel: t("createListing.sectionComplete"),
			};
		}
		if (state.status === "error") {
			return {
				status: "error" as const,
				statusLabel: t("createListing.sectionRemaining", {
					count: state.remaining,
				}),
			};
		}
		return { status: "neutral" as const };
	};

	// Scroll anchor for scrollToSection(); keeps the section title clear of
	// any sticky chrome.
	const sectionAnchor = (key: SectionKey) => ({
		"data-section-key": key,
		style: { scrollMarginTop: 12 },
	});

	// Apply the Sprint 1 visibility matrix: when (property_type, deal_type)
	// changes, wipe fields that are no longer visible. Rule P3 (land forces
	// sell) is applied via normalizeCombo before computing the clearing patch.
	const applyTransition = (nextPt: PropertyType, nextDt: DealType) => {
		const norm = normalizeCombo(nextPt, nextDt);
		const patch = clearIncompatibleFields(
			norm.propertyType,
			norm.dealType,
		) as Partial<ListingFormValues>;
		// Land rents long-term only — the rent-period selector is hidden for
		// land, so the value is pinned here to keep the field required-filled.
		if (norm.propertyType === "land" && norm.dealType === "rent") {
			patch.rent_period = "long_term";
		}
		// «Под жилое строительство» is a sale-only purpose; the rent option
		// list hides it, so drop a stale value when the deal flips to rent.
		if (
			norm.dealType === "rent" &&
			form.values.land_purpose === "construction"
		) {
			patch.land_purpose = undefined;
		}
		form.setValues({
			...form.values,
			property_type: norm.propertyType,
			type: norm.dealType,
			...patch,
		});
	};

	return (
		<>
			{/* ── Type ── */}
			<div {...sectionAnchor("type")}>
			<FormSection
				title={t("createListing.listingType")}
				bg={sectionBg}
				{...sectionStatusProps("type")}
			>
				<ChipSelect
					label={t("createListing.propertyType")}
					required
					options={[
						{ value: "apartment", label: t("propertyTypes.apartment") },
						{ value: "house", label: t("propertyTypes.house") },
						{ value: "land", label: t("propertyTypes.land") },
						{ value: "commercial", label: t("propertyTypes.commercial") },
					]}
					value={form.values.property_type}
					onChange={(val) => {
						const nextPt =
							(val as ListingFormValues["property_type"]) || "apartment";
						applyTransition(nextPt, form.values.type);
					}}
					error={form.errors.property_type as string}
				/>
				{/* Classifier right under the property type — industry funnel is
				    «what exactly is it» before sizes (OLX/Avito/Cian ask
				    вторичка/новостройка, тип дома, офис/склад at category level). */}
				{show.commercialType && (
					<ChipSelect
						label={t("createListing.commercialTypeLabel")}
						required
						options={commercialTypeOpts}
						value={form.values.commercial_type}
						onChange={(val) =>
							set("commercial_type", val as string | undefined)
						}
						error={form.errors.commercial_type as string}
					/>
				)}
				{show.houseType && (
					<ChipSelect
						label={t("createListing.houseType")}
						options={houseTypeOpts}
						value={form.values.house_type}
						onChange={(val) => set("house_type", val as string | undefined)}
					/>
				)}
				{show.marketType && (
					<ChipSelect
						label={t("createListing.marketTypeLabel")}
						required
						options={marketTypeOpts}
						value={form.values.market_type}
						onChange={(val) => set("market_type", val as string | undefined)}
						error={form.errors.market_type as string}
					/>
				)}
				<ChipSelect
					label={t("createListing.dealType")}
					required
					options={[
						{ label: t("createListing.sell"), value: "sell" },
						{ label: t("createListing.rent"), value: "rent" },
					]}
					value={form.values.type}
					onChange={(val) => {
						const nextDt = (val as DealType) || "sell";
						applyTransition(pt, nextDt);
					}}
					error={form.errors.type as string}
				/>
				{/* Rent group — lives right under the deal type so it appears the
				    moment «Аренда» is picked (was in the Price section before). */}
				{show.rentPeriod && (
					<ChipSelect
						label={t("createListing.rentPeriodLabel")}
						required
						options={[
							{
								value: "long_term",
								label: t("createListing.rentPeriodLongTerm"),
							},
							{
								value: "daily",
								// «Посуточно» is housing vocabulary; commercial days
								// are rented «на день» (halls, studios, venues).
								label:
									pt === "commercial"
										? t("createListing.rentPeriodDailyCommercial")
										: t("createListing.rentPeriodDaily"),
							},
						]}
						value={form.values.rent_period}
						onChange={(val) => {
							const next = val as string | undefined;
							set("rent_period", next);
							// P4 sub-gate: min_rent_months only applies to long_term —
							// drop a stale value when switching away.
							if (next !== "long_term" && form.values.min_rent_months) {
								set("min_rent_months", undefined);
							}
						}}
						error={form.errors.rent_period as string}
					/>
				)}
				{show.minRentMonths && form.values.rent_period === "long_term" && (
					<ChipSelect
						label={t("createListing.minRentMonthsLabel")}
						required
						options={[
							{ value: "1", label: "1" },
							{ value: "3", label: "3" },
							{ value: "6", label: "6" },
							{ value: "12", label: "12" },
						]}
						value={form.values.min_rent_months}
						onChange={(val) =>
							set("min_rent_months", val as number | undefined)
						}
						customInputMode="numeric"
						customPlaceholder="2, 9, 24..."
						error={form.errors.min_rent_months as string}
					/>
				)}
				{/* S3 — urgent_flag (always-visible, defaults to false). */}
				<Switch
					label={t("createListing.urgentFlag")}
					description={t("createListing.urgentFlagDescription")}
					checked={form.values.urgent_flag}
					onChange={(e) => set("urgent_flag", e.currentTarget.checked)}
					styles={{ label: { fontWeight: 500, fontSize: 14 } }}
				/>
			</FormSection>
			</div>

			{/* ── Parameters ── */}
			{/* Field order changes by property type: houses prioritize land area + stories.
			    Rendered only when the current combo has at least one parameter field,
			    so the section never shows up as an empty card. */}
			{(show.landArea ||
				show.rooms ||
				show.area ||
				show.livingArea ||
				show.kitchenArea ||
				show.floor ||
				show.totalFloors ||
				show.ceilingHeight) && (
			<div {...sectionAnchor("parameters")}>
			<FormSection
				title={t("createListing.parameters")}
				bg={sectionBg}
				{...sectionStatusProps("parameters")}
			>
				{/* Land area — first for houses and land */}
				{show.landArea && (
					<ChipSelect
						label={t("createListing.landArea")}
						options={landAreaOpts}
						value={form.values.land_area}
						onChange={(val) => set("land_area", val as number | undefined)}
						customInputMode="decimal"
						customPlaceholder="25, 50..."
					/>
				)}
				{show.rooms && (
					<ChipSelect
						label={t("createListing.rooms")}
						required
						options={roomOpts}
						value={form.values.rooms}
						onChange={(val) => set("rooms", val as number | undefined)}
						customInputMode="numeric"
						customPlaceholder="7, 8, 10..."
						error={form.errors.rooms as string}
					/>
				)}
				{show.area && (
					<ChipSelect
						label={t("createListing.totalArea")}
						required
						options={areaOpts}
						value={form.values.area}
						onChange={(val) => set("area", val as number | undefined)}
						customInputMode="decimal"
						customPlaceholder="94.5, 120..."
						error={form.errors.area as string}
					/>
				)}
				{show.livingArea && (
					<ChipSelect
						label={t("createListing.livingArea")}
						options={livingAreaOpts}
						value={form.values.living_area}
						onChange={(val) => set("living_area", val as number | undefined)}
						customInputMode="decimal"
					/>
				)}
				{show.kitchenArea && (
					<ChipSelect
						label={t("createListing.kitchenArea")}
						options={kitchenAreaOpts}
						value={form.values.kitchen_area}
						onChange={(val) => set("kitchen_area", val as number | undefined)}
						customInputMode="decimal"
					/>
				)}
				{/* Floor — apartments/commercial only, never for houses */}
				{show.floor && (
					<ChipSelect
						label={t("createListing.floor")}
						required
						options={floorOpts}
						value={form.values.floor}
						onChange={(val) => set("floor", val as number | undefined)}
						customInputMode="numeric"
						customPlaceholder="10, 15..."
						error={form.errors.floor as string}
					/>
				)}
				{/* Total floors — after individual floor */}
				{show.totalFloors && (
					<ChipSelect
						label={
							pt === "house"
								? t("createListing.houseStories")
								: t("createListing.totalFloors")
						}
						required
						options={totalFloorsOpts}
						value={form.values.total_floors}
						onChange={(val) => set("total_floors", val as number | undefined)}
						customInputMode="numeric"
						customPlaceholder="24, 30..."
						error={form.errors.total_floors as string}
					/>
				)}
				{/* Ceiling height — optional, all property types except land */}
				{show.ceilingHeight && (
					<ChipSelect
						label={t("createListing.ceilingHeightLabel")}
						options={ceilingHeightOpts}
						value={form.values.ceiling_height}
						onChange={(val) =>
							set("ceiling_height", val as number | undefined)
						}
						customInputMode="decimal"
						customPlaceholder="2.8, 4.5..."
					/>
				)}
			</FormSection>
			</div>
			)}

			{/* ── Apartment Attributes (apartment only) ── */}
			{/* market_type lifted into the Type section as the classifier. */}
			{pt !== "house" &&
				(show.condition ||
					show.furniture ||
					show.wallMaterial ||
					show.balcony ||
					show.listingSubtype ||
					show.floorPlanUrl) && (
				<div {...sectionAnchor("aptAttributes")}>
				<FormSection
					title={t("createListing.aptAttributes")}
					bg={sectionBg}
					{...sectionStatusProps("aptAttributes")}
				>
					{show.condition && (
						<ChipSelect
							label={t("createListing.condition")}
							required
							options={conditionOpts}
							value={form.values.condition}
							onChange={(val) => set("condition", val as string | undefined)}
							error={form.errors.condition as string}
						/>
					)}
					{show.furniture && (
						<ChipSelect
							label={t("createListing.furnitureLabel")}
							required
							options={furnitureOpts}
							value={form.values.furniture}
							onChange={(val) => set("furniture", val as string | undefined)}
							error={form.errors.furniture as string}
						/>
					)}
					{show.wallMaterial && (
						<ChipSelect
							label={t("createListing.wallMaterialLabel")}
							options={wallMaterialOpts}
							value={form.values.wall_material}
							onChange={(val) =>
								set("wall_material", val as string | undefined)
							}
						/>
					)}
					{show.listingSubtype && (
						<ChipSelect
							label={t("createListing.listingSubtypeLabel")}
							options={listingSubtypeOpts}
							value={form.values.listing_subtype}
							onChange={(val) =>
								set("listing_subtype", val as string | undefined)
							}
						/>
					)}
					{show.balcony && (
						<ChipSelect
							label={t("createListing.balconyLabel")}
							options={balconyOpts}
							value={form.values.balcony}
							onChange={(val) => set("balcony", val as string | undefined)}
						/>
					)}
					{show.floorPlanUrl && (
						<TextInput
							label={optionalLabel(t("createListing.floorPlanUrlLabel"))}
							placeholder={t("createListing.floorPlanUrlPlaceholder")}
							value={form.values.floor_plan_url || ""}
							onChange={(e) =>
								set("floor_plan_url", e.currentTarget.value || undefined)
							}
						/>
					)}
				</FormSection>
				</div>
			)}

			{/* ── House-Specific Attributes ── */}
			{(show.houseType || show.garage || show.basement) && (
				<div {...sectionAnchor("houseAttributes")}>
				<FormSection
					title={t("createListing.houseAttributes")}
					bg={sectionBg}
					{...sectionStatusProps("houseAttributes")}
				>
					{/* house_type lifted into the Type section as the classifier;
					    show.houseType still gates the house-only multiselects. */}
					{show.houseType && (
						<ChipMultiSelect
							label={t("createListing.houseCondition")}
							description={t("createListing.multipleAllowed")}
							options={houseConditionOpts}
							value={form.values.house_condition}
							onChange={(val) => set("house_condition", val)}
						/>
					)}
					{show.houseType && (
						<ChipMultiSelect
							label={t("createListing.locationType")}
							description={t("createListing.multipleAllowed")}
							options={locationTypeOpts}
							value={form.values.location_type}
							onChange={(val) => set("location_type", val)}
						/>
					)}
					{show.furniture && (
						<ChipSelect
							label={t("createListing.furnitureLabel")}
							required
							options={furnitureOpts}
							value={form.values.furniture}
							onChange={(val) => set("furniture", val as string | undefined)}
							error={form.errors.furniture as string}
						/>
					)}
					{show.wallMaterial && (
						<ChipSelect
							label={t("createListing.wallMaterialLabel")}
							options={wallMaterialOpts}
							value={form.values.wall_material}
							onChange={(val) =>
								set("wall_material", val as string | undefined)
							}
						/>
					)}
					{/* S6 — house polish booleans */}
					{show.garage && (
						<Switch
							label={t("createListing.garageLabel")}
							checked={form.values.garage === true}
							onChange={(e) =>
								set("garage", e.currentTarget.checked || undefined)
							}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					)}
					{show.basement && (
						<Switch
							label={t("createListing.basementLabel")}
							checked={form.values.basement === true}
							onChange={(e) =>
								set("basement", e.currentTarget.checked || undefined)
							}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					)}
				</FormSection>
				</div>
			)}

			{/* ── Utilities (House only) ── */}
			{show.utilities && (
				<div {...sectionAnchor("utilities")}>
				<FormSection
					title={t("createListing.utilities")}
					bg={sectionBg}
					{...sectionStatusProps("utilities")}
				>
					<ChipMultiSelect
						label={t("createListing.waterSupply")}
						description={t("createListing.multipleAllowed")}
						options={waterSupplyOpts}
						value={form.values.water_supply}
						onChange={(val) => set("water_supply", val)}
					/>
					<ChipSelect
						label={t("createListing.electricity")}
						options={yesNoPossibleOpts}
						value={form.values.electricity}
						onChange={(val) => set("electricity", val as string | undefined)}
					/>
					<ChipMultiSelect
						label={t("createListing.heating")}
						description={t("createListing.multipleAllowed")}
						options={heatingOpts}
						value={form.values.heating}
						onChange={(val) => set("heating", val)}
					/>
					<ChipSelect
						label={t("createListing.gasSupply")}
						options={yesNoPossibleOpts}
						value={form.values.gas_supply}
						onChange={(val) => set("gas_supply", val as string | undefined)}
					/>
					<ChipSelect
						label={t("createListing.sewage")}
						options={sewageOpts}
						value={form.values.sewage}
						onChange={(val) => set("sewage", val as string | undefined)}
					/>
				</FormSection>
				</div>
			)}

			{/* ── Land Purpose + S6 land polish (Land only) ── */}
			{(show.landPurpose ||
				show.buildingsExist ||
				show.fence ||
				show.landShape) && (
				<div {...sectionAnchor("landPurpose")}>
				<FormSection
					title={t("createListing.landPurposeSection")}
					bg={sectionBg}
					{...sectionStatusProps("landPurpose")}
				>
					{show.landPurpose && (
						<ChipSelect
							label={t("createListing.landPurpose")}
							options={landPurposeOpts}
							value={form.values.land_purpose}
							onChange={(val) => set("land_purpose", val as string | undefined)}
						/>
					)}
					{show.landShape && (
						<ChipSelect
							label={t("createListing.landShapeLabel")}
							options={landShapeOpts}
							value={form.values.land_shape}
							onChange={(val) => set("land_shape", val as string | undefined)}
						/>
					)}
					{show.buildingsExist && (
						<Switch
							label={t("createListing.buildingsExistLabel")}
							checked={form.values.buildings_exist === true}
							onChange={(e) =>
								set("buildings_exist", e.currentTarget.checked || undefined)
							}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					)}
					{show.fence && (
						<Switch
							label={t("createListing.fenceLabel")}
							checked={form.values.fence === true}
							onChange={(e) =>
								set("fence", e.currentTarget.checked || undefined)
							}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					)}
				</FormSection>
				</div>
			)}

			{/* ── Commercial Attributes (S4) ── */}
			{/* commercial_type lifted into the Type section as the classifier. */}
			{(show.entrance || show.parkingComm || show.buildingClass) && (
				<div {...sectionAnchor("commercial")}>
				<FormSection
					title={t("createListing.commercialSection")}
					bg={sectionBg}
					{...sectionStatusProps("commercial")}
				>
					{show.buildingClass && (
						<ChipSelect
							label={t("createListing.buildingClassLabel")}
							options={buildingClassOpts}
							value={form.values.building_class}
							onChange={(val) =>
								set("building_class", val as string | undefined)
							}
						/>
					)}
					{show.entrance && (
						<ChipSelect
							label={t("createListing.entranceLabel")}
							options={entranceOpts}
							value={form.values.entrance}
							onChange={(val) => set("entrance", val as string | undefined)}
						/>
					)}
					{show.parkingComm && (
						<Switch
							label={t("createListing.parkingCommLabel")}
							checked={form.values.parking_comm === true}
							onChange={(e) =>
								set("parking_comm", e.currentTarget.checked || undefined)
							}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					)}
				</FormSection>
				</div>
			)}

			{/* ── Amenities ── */}
			{(show.aptAmenities || show.houseAmenities || show.nearbyAmenities) && (
				<div {...sectionAnchor("amenities")}>
				<FormSection
					title={t("createListing.amenitiesSection")}
					bg={sectionBg}
					{...sectionStatusProps("amenities")}
				>
					{show.aptAmenities && (
						<ChipMultiSelect
							label={t("createListing.inProperty")}
							description={t("createListing.multipleAllowed")}
							options={aptAmenityOpts}
							value={form.values.amenities}
							onChange={(val) => set("amenities", val)}
						/>
					)}
					{show.houseAmenities && (
						<ChipMultiSelect
							label={t("createListing.inHouseProperty")}
							description={t("createListing.multipleAllowed")}
							options={houseAmenityOpts}
							value={form.values.amenities}
							onChange={(val) => set("amenities", val)}
						/>
					)}
					{show.nearbyAmenities && (
						<ChipMultiSelect
							label={t("createListing.nearby")}
							description={t("createListing.multipleAllowed")}
							options={nearbyOpts}
							value={form.values.nearby_amenities}
							onChange={(val) => set("nearby_amenities", val)}
						/>
					)}
				</FormSection>
				</div>
			)}

			{/* ── Location ── */}
			<div {...sectionAnchor("location")}>
			<FormSection
				title={t("createListing.locationSection")}
				bg={sectionBg}
				{...sectionStatusProps("location")}
			>
				<ChipSelect
					label={t("createListing.region")}
					required
					options={regions}
					value={form.values.region || undefined}
					onChange={(val) => {
						const next = val ? String(val) : "";
						onRegionChange(next);
						// P5 sub-gate (mirrors backend _clear_incompatible_fields):
						// metro_station is only meaningful inside Tashkent. Wipe
						// it whenever the region leaves.
						if (next !== TASHKENT_REGION && form.values.metro_station) {
							set("metro_station", undefined);
						}
					}}
					error={form.errors.region as string}
				/>
				{form.values.region && districts.length > 0 && (
					<ChipSelect
						label={t("createListing.district")}
						required
						options={districts}
						value={form.values.district || undefined}
						onChange={(val) => {
							const nextDistrict = val ? String(val) : "";
							set("district", nextDistrict);
							// Cascade: drop a metro station that is not in the newly
							// selected district (mirrors the P5 region clear).
							if (
								form.values.metro_station &&
								!METRO_STATIONS.some(
									(s) =>
										s.key === form.values.metro_station &&
										s.district === nextDistrict,
								)
							) {
								set("metro_station", undefined);
							}
						}}
						error={form.errors.district as string}
					/>
				)}
				{districtChosen && (
					<MicrodistrictAutocomplete
						label={optionalLabel(t("createListing.microdistrictLabel"))}
						placeholder={t("createListing.microdistrictPlaceholder")}
						district={form.values.district || undefined}
						value={form.values.microdistrict || undefined}
						onChange={(val) => set("microdistrict", val)}
					/>
				)}
				{/* S3 — metro_station: shown only after the user picks a district
				    that has stations (prevents the full 49-station list appearing
				    immediately when Tashkent is selected). */}
				{show.metroStation && metroDistrictHasStations && (
					<MetroStationAutocomplete
						label={optionalLabel(t("createListing.metroStationLabel"))}
						placeholder={t(
							"createListing.metroStationPlaceholder",
							"Начните вводить название…",
						)}
						district={metroDistrict}
						value={form.values.metro_station}
						onChange={(key) => set("metro_station", key)}
					/>
				)}
				{/* S3 — landmark / PR-G — catalog hints (район→ориентир cascade).
				    Free-text is always accepted; landmark_id wiring is a
				    follow-up, so the form still submits the free-text name. */}
				{districtChosen && (
					<LandmarkAutocomplete
						label={optionalLabel(t("createListing.landmarkLabel"))}
						placeholder={t("createListing.landmarkPlaceholder")}
						region={form.values.region || undefined}
						district={form.values.district || undefined}
						value={{ landmark_id: undefined, landmark: form.values.landmark }}
						onChange={({ landmark }) => set("landmark", landmark)}
					/>
				)}
				{/* S3 — jk_name / S7 — jk_id (matrix-gated to apartment + house) */}
				{show.jkName && districtChosen && (
					<HousingComplexAutocomplete
						label={optionalLabel(t("createListing.jkNameLabel"))}
						placeholder={t("createListing.jkNamePlaceholder")}
						region={form.values.region || undefined}
						district={form.values.district || undefined}
						value={{
							jk_id: form.values.jk_id,
							jk_name: form.values.jk_name,
						}}
						onChange={({ jk_id, jk_name }) => {
							set("jk_id", jk_id);
							set("jk_name", jk_name);
						}}
					/>
				)}
				<Box>
					<Text size="sm" fw={500} mb={6}>
						{t("createListing.mapLabel")}
						<Text span c="red" inherit>
							{" "}
							*
						</Text>
					</Text>
					<Suspense
						fallback={<Box h={220} bg="gray.1" style={{ borderRadius: 12 }} />}
					>
						<MapPicker
							lat={form.values.latitude ?? null}
							lng={form.values.longitude ?? null}
							centerLat={locationCenter?.lat}
							centerLng={locationCenter?.lng}
							centerZoom={locationCenter?.zoom}
							onChange={(lat, lng) => {
								set("latitude", lat);
								set("longitude", lng);
							}}
							onAddressResolved={(addr) => set("address", addr)}
						/>
					</Suspense>
					{form.errors.latitude && (
						<Text size="xs" c="red" mt={4}>
							{form.errors.latitude as string}
						</Text>
					)}
				</Box>
				{form.values.address ? (
					<Box>
						<Text size="sm" fw={500} mb={4} c="dimmed">
							{t("createListing.addressLabel")}
						</Text>
						<Text size="sm" c="dimmed" lh={1.5}>
							{form.values.address}
						</Text>
					</Box>
				) : null}
			</FormSection>
			</div>

			{/* ── Description + optional AI block ── */}
			<div {...sectionAnchor("description")}>
			<FormSection
				title={t("createListing.additionalInfo")}
				bg={sectionBg}
				{...sectionStatusProps("description")}
			>
				{beforeDescriptionContent}
				<Box>
					<Box style={{ position: "relative" }}>
						<Textarea
							placeholder={t("createListing.descriptionPlaceholder")}
							maxLength={descriptionValueOverride !== undefined ? undefined : 500}
							value={
								descriptionValueOverride !== undefined
									? descriptionValueOverride
									: (form.values.description ?? "")
							}
							onChange={(e) => {
								if (onDescriptionChangeOverride) {
									onDescriptionChangeOverride(e.currentTarget.value);
								} else {
									form.getInputProps("description").onChange(e);
								}
							}}
							onBlur={form.getInputProps("description").onBlur}
							error={form.errors.description as string | undefined}
							disabled={descriptionLoading}
							autosize
							minRows={3}
							styles={{ input: { minHeight: 80 } }}
						/>
						{/* AI progress lives inside the field (industry pattern):
						    pulsing skeleton lines + caption over the textarea. */}
						{descriptionLoading && (
							<Box
								style={{
									position: "absolute",
									inset: 0,
									borderRadius: 8,
									backgroundColor: "rgba(255,255,255,0.92)",
									display: "flex",
									flexDirection: "column",
									justifyContent: "center",
									gap: 8,
									padding: "14px 16px",
								}}
							>
								<Skeleton height={9} width="92%" radius="xl" />
								<Skeleton height={9} width="100%" radius="xl" />
								<Skeleton height={9} width="74%" radius="xl" />
								<Group gap={8} mt={4}>
									<Loader size="xs" color="blue" />
									<Text size="xs" fw={600} c="blue.7">
										{t(
											"createListing.generatingText",
											"Составляем описание… ≈15 сек",
										)}
									</Text>
								</Group>
							</Box>
						)}
					</Box>
					{descriptionValueOverride === undefined && (
						<Box
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								marginTop: 4,
							}}
						>
							<Text
								size="xs"
								c={
									(form.values.description?.length ?? 0) >= 500
										? "red"
										: "transparent"
								}
							>
								{t("createListing.charLimitReached", { count: 500 })}
							</Text>
							<Text
								size="xs"
								c={
									(form.values.description?.length ?? 0) >= 500
										? "red"
										: "dimmed"
								}
							>
								{form.values.description?.length ?? 0} / 500
							</Text>
						</Box>
					)}
				</Box>
				{afterDescriptionContent}
			</FormSection>
			</div>

			{/* ── Price ── */}
			<div {...sectionAnchor("price")}>
			<FormSection
				title={t("createListing.priceSection")}
				bg={sectionBg}
				{...sectionStatusProps("price")}
			>
				{/* Price: label on its own full-width line (rent labels are long
				    and must not wrap), then the input + negotiable toggle in one
				    row. When «Договорная» is on the input is disabled
				    (buildListingData sends price: 0). The chosen currency is
				    made explicit inside the field: $ prefix / «сум» suffix. */}
				<Box>
					<Text size="sm" fw={500} mb={6}>
						{priceLabel}
						<Text span c="red" inherit>
							{" "}
							*
						</Text>
					</Text>
					<Group wrap="nowrap" gap="sm" align="center">
						<NumberInput
							min={0}
							allowNegative={false}
							allowDecimal={false}
							thousandSeparator=" "
							inputMode="numeric"
							hideControls
							prefix={form.values.currency === "USD" ? "$ " : undefined}
							suffix={
								form.values.currency === "UZS"
									? ` ${t("createListing.sumSuffix", "сум")}`
									: undefined
							}
							disabled={form.values.is_negotiable}
							style={{ flex: 1 }}
							error={form.errors.price}
							rightSection={
								form.values.price != null && !form.values.is_negotiable ? (
									<ActionIcon
										variant="transparent"
										color="gray"
										size="sm"
										onClick={() => set("price", undefined)}
									>
										<IconX size={14} />
									</ActionIcon>
								) : null
							}
							{...form.getInputProps("price")}
						/>
						<Switch
							label={t("createListing.negotiable")}
							checked={form.values.is_negotiable}
							onChange={(e) => set("is_negotiable", e.currentTarget.checked)}
							styles={{ label: { fontWeight: 500, fontSize: 14 } }}
						/>
					</Group>
				</Box>
				<ChipSelect
					label={t("createListing.currencyLabel")}
					showOptionalHint={false}
					options={currencyOpts}
					value={form.values.currency}
					onChange={(val) => set("currency", (val as "USD" | "UZS") || "USD")}
				/>
			</FormSection>
			</div>

			{/* ── Contact ── */}
			<div {...sectionAnchor("contact")}>
			<FormSection
				title={t("createListing.contactSection")}
				bg={sectionBg}
				{...sectionStatusProps("contact")}
			>
				{verifiedPhones.length >= 1 ? (
					<Select
						label={t("listingForm.phoneSelect.label", {
							defaultValue: "Контактный номер",
						})}
						placeholder={t("listingForm.phoneSelect.placeholder", {
							defaultValue: "Выберите номер",
						})}
						description={t("phones.contactPhoneHint", {
							defaultValue: "Можно выбрать любой из ваших подтверждённых номеров",
						})}
						data={[
							...verifiedPhones.map((p) => ({
								value: p.phone,
								label: p.is_primary
									? `${p.phone} (${t("phones.primaryBadge", { defaultValue: "Основной" })})`
									: p.phone,
							})),
							// Action row pinned to the bottom of the dropdown.
							{
								value: ADD_CONTACT_OPTION,
								label: t("listingForm.addContactLink", {
									defaultValue: "+ Добавить контакт",
								}),
							},
						]}
						value={
							verifiedPhones.some((p) => p.phone === form.values.phone)
								? form.values.phone
								: null
						}
						onChange={(val) => {
							if (val === ADD_CONTACT_OPTION) {
								navigate("/edit-profile");
								return;
							}
							set("phone", val || "");
						}}
						renderOption={({ option }) =>
							option.value === ADD_CONTACT_OPTION ? (
								<Text size="sm" c="blue.6" fw={600}>
									{option.label}
								</Text>
							) : (
								<Text size="sm">{option.label}</Text>
							)
						}
						// The section sits at the page bottom: lift the dropdown
						// above the fixed action bar (zIndex 10001) and cap its
						// height so «+ Добавить контакт» is always reachable.
						comboboxProps={{ zIndex: 10002 }}
						maxDropdownHeight={240}
						clearable={false}
					/>
				) : (
					<>
						<PhoneInput
							label={t("createListing.phoneLabel")}
							placeholder="+998 XX XXX XX XX"
							description={t("createListing.phoneDescription")}
							value={form.values.phone}
							onChange={(val) => set("phone", val)}
							error={form.errors.phone as string}
							onClear={() => set("phone", "")}
						/>
						<Anchor
							component="button"
							size="sm"
							onClick={() => navigate("/edit-profile")}
							style={{ display: "block", marginTop: 4 }}
						>
							{t("listingForm.addContactLink", {
								defaultValue: "+ Добавить контакт",
							})}
						</Anchor>
					</>
				)}
			</FormSection>
			</div>
		</>
	);
}
