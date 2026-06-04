import {
	Textarea,
	NumberInput,
	Box,
	Text,
	Switch,
	TextInput,
	Select,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { FormSection } from "@shared/ui/FormSection";
import { ChipSelect } from "@shared/ui/ChipSelect";
import { ChipMultiSelect } from "@shared/ui/ChipMultiSelect";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { HousingComplexAutocomplete } from "@shared/ui/HousingComplexAutocomplete";
import { resolveLocationCoords } from "@shared/constants/locationCoords";
import { apiClient } from "@shared/api/client";
import type { UseFormReturnType } from "@mantine/form";
import type { ListingFormValues } from "./useListingForm";
import {
	clearIncompatibleFields,
	isVisible,
	normalizeCombo,
} from "../lib/visibility";
import type { DealType, PropertyType } from "../lib/visibility";

// P5 sub-gate (blueprint §2.2): metro_station is only meaningful inside
// Tashkent. Mirrors backend `_clear_incompatible_fields` rule P5.
const TASHKENT_REGION = "toshkent_shahri";

const MapPicker = lazy(() =>
	import("@shared/ui/MapPicker").then((m) => ({ default: m.MapPicker })),
);

interface ListingFormFieldsProps {
	form: UseFormReturnType<ListingFormValues>;
	regions: { value: string; label: string }[];
	districts: { value: string; label: string }[];
	onRegionChange: (value: string) => void;
	sectionBg?: string;
}

export function ListingFormFields({
	form,
	regions,
	districts,
	onRegionChange,
	sectionBg,
}: ListingFormFieldsProps) {
	const { t } = useTranslation("seller");
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
			pricePerSqm: isVisible("price_per_sqm", pt, dt),
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
			floorPlanUrl: isVisible("floor_plan_url", pt, dt),
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
		{
			value: "0",
			label: t("createListing.studio"),
		},
		{ value: "1", label: "1" },
		{ value: "2", label: "2" },
		{ value: "3", label: "3" },
		{ value: "4", label: "4" },
		{ value: "5", label: "5" },
		{ value: "6", label: "6" },
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
		{ value: "1", label: "1 sotka" },
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

	// House-specific options
	const houseTypeOpts = [
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
	// Simple list for the MVP; a later PR can source this from a static
	// data module if the set grows.
	const metroStationOpts = [
		{ value: "chilonzor", label: "Chilonzor" },
		{ value: "mustaqillik_maydoni", label: "Mustaqillik Maydoni" },
		{ value: "amir_temur_xiyoboni", label: "Amir Temur Xiyoboni" },
		{ value: "yunus_rajabiy", label: "Yunus Rajabiy" },
		{ value: "minor", label: "Minor" },
		{ value: "beruniy", label: "Beruniy" },
		{ value: "pushkin", label: "Pushkin" },
		{ value: "ming_urik", label: "Ming O'rik" },
		{ value: "oybek", label: "Oybek" },
		{ value: "kosmonavtlar", label: "Kosmonavtlar" },
		{ value: "olmazor", label: "Olmazor" },
		{ value: "sergeli", label: "Sergeli" },
	];

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
		{ value: "balcony", label: t("createListing.amenBalcony") },
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
	const landPurposeOpts = [
		{ value: "construction", label: t("createListing.lpConstruction") },
		{
			value: "commercial_land",
			label: t("createListing.lpCommercialLand"),
		},
		{ value: "agricultural", label: t("createListing.lpAgricultural") },
		{ value: "garden", label: t("createListing.lpGarden") },
		{ value: "unspecified", label: t("createListing.lpUnspecified") },
	];

	const currencyOpts = [
		{ value: "USD", label: t("createListing.currencyUSD") },
		{ value: "UZS", label: t("createListing.currencyUZS") },
	];

	const set = (key: string, val: any) => form.setFieldValue(key, val);

	// Apply the Sprint 1 visibility matrix: when (property_type, deal_type)
	// changes, wipe fields that are no longer visible. Rule P3 (land forces
	// sell) is applied via normalizeCombo before computing the clearing patch.
	const applyTransition = (nextPt: PropertyType, nextDt: DealType) => {
		const norm = normalizeCombo(nextPt, nextDt);
		const patch = clearIncompatibleFields(
			norm.propertyType,
			norm.dealType,
		) as Partial<ListingFormValues>;
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
			<FormSection title={t("createListing.listingType")} bg={sectionBg}>
				<ChipSelect
					label={t("createListing.propertyType")}
					required
					options={[
						{ value: "apartment", label: t("propertyTypes.apartment") },
						{ value: "house", label: t("propertyTypes.house") },
						{ value: "commercial", label: t("propertyTypes.commercial") },
						{ value: "land", label: t("propertyTypes.land") },
					]}
					value={form.values.property_type}
					onChange={(val) => {
						const nextPt =
							(val as ListingFormValues["property_type"]) || "apartment";
						applyTransition(nextPt, form.values.type);
					}}
					error={form.errors.property_type as string}
				/>
				{pt !== "land" && (
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
				)}
			</FormSection>

			{/* ── Parameters ── */}
			{/* Field order changes by property type: houses prioritize land area + stories */}
			<FormSection title={t("createListing.parameters")} bg={sectionBg}>
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
			</FormSection>

			{/* ── Apartment / Shared Attributes ── */}
			{(show.marketType ||
				show.condition ||
				show.furniture ||
				show.wallMaterial ||
				show.balcony ||
				show.listingSubtype ||
				show.floorPlanUrl) && (
				<FormSection title={t("createListing.aptAttributes")} bg={sectionBg}>
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
							label={t("createListing.floorPlanUrlLabel")}
							placeholder={t("createListing.floorPlanUrlPlaceholder")}
							value={form.values.floor_plan_url || ""}
							onChange={(e) =>
								set("floor_plan_url", e.currentTarget.value || undefined)
							}
						/>
					)}
				</FormSection>
			)}

			{/* ── House-Specific Attributes ── */}
			{(show.houseType || show.garage || show.basement) && (
				<FormSection title={t("createListing.houseAttributes")} bg={sectionBg}>
					{show.houseType && (
						<ChipSelect
							label={t("createListing.houseType")}
							options={houseTypeOpts}
							value={form.values.house_type}
							onChange={(val) => set("house_type", val as string | undefined)}
						/>
					)}
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
			)}

			{/* ── Utilities (House only) ── */}
			{show.utilities && (
				<FormSection title={t("createListing.utilities")} bg={sectionBg}>
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
			)}

			{/* ── Land Purpose + S6 land polish (Land only) ── */}
			{(show.landPurpose ||
				show.buildingsExist ||
				show.fence ||
				show.landShape) && (
				<FormSection
					title={t("createListing.landPurposeSection")}
					bg={sectionBg}
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
			)}

			{/* ── Commercial Attributes (S4) ── */}
			{(show.commercialType ||
				show.pricePerSqm ||
				show.ceilingHeight ||
				show.entrance ||
				show.parkingComm ||
				show.buildingClass) && (
				<FormSection
					title={t("createListing.commercialSection")}
					bg={sectionBg}
				>
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
					{show.ceilingHeight && (
						<NumberInput
							label={t("createListing.ceilingHeightLabel")}
							min={0.1}
							max={30}
							step={0.1}
							decimalScale={1}
							hideControls
							value={form.values.ceiling_height ?? ""}
							onChange={(val) =>
								set("ceiling_height", typeof val === "number" ? val : undefined)
							}
						/>
					)}
					{show.pricePerSqm && (
						<NumberInput
							label={t("createListing.pricePerSqmLabel")}
							min={0}
							allowNegative={false}
							allowDecimal={false}
							thousandSeparator=" "
							hideControls
							value={form.values.price_per_sqm ?? ""}
							onChange={(val) =>
								set("price_per_sqm", typeof val === "number" ? val : undefined)
							}
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
			)}

			{/* ── Amenities ── */}
			{(show.aptAmenities || show.houseAmenities || show.nearbyAmenities) && (
				<FormSection title={t("createListing.amenitiesSection")} bg={sectionBg}>
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
			)}

			{/* ── Location ── */}
			<FormSection title={t("createListing.locationSection")} bg={sectionBg}>
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
							set("district", val ? String(val) : "");
						}}
						error={form.errors.district as string}
					/>
				)}
				{/* S3 — always-visible city (required on CREATE) */}
				<TextInput
					label={t("createListing.cityLabel")}
					placeholder={t("createListing.cityPlaceholder")}
					required
					value={form.values.city}
					onChange={(e) => set("city", e.currentTarget.value)}
					error={form.errors.city as string}
				/>
				{/* S3 — always-visible microdistrict */}
				<TextInput
					label={t("createListing.microdistrictLabel")}
					placeholder={t("createListing.microdistrictPlaceholder")}
					value={form.values.microdistrict || ""}
					onChange={(e) =>
						set("microdistrict", e.currentTarget.value || undefined)
					}
				/>
				{/* S3 — jk_name / S7 — jk_id (matrix-gated to apartment + house).
				    Autocomplete resolves to jk_id on pick; free-text keeps jk_id
				    undefined and stores the name in jk_name. Both columns are
				    valid during the dual-column window. */}
				{show.jkName && (
					<HousingComplexAutocomplete
						label={t("createListing.jkNameLabel")}
						placeholder={t("createListing.jkNamePlaceholder")}
						region={form.values.region || undefined}
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
				{/* S3 — metro_station (matrix + P5 region sub-gate) */}
				{show.metroStation && (
					<ChipSelect
						label={t("createListing.metroStationLabel")}
						options={metroStationOpts}
						value={form.values.metro_station}
						onChange={(val) => set("metro_station", val as string | undefined)}
					/>
				)}
				{/* S3 — always-visible landmark */}
				<TextInput
					label={t("createListing.landmarkLabel")}
					placeholder={t("createListing.landmarkPlaceholder")}
					value={form.values.landmark || ""}
					onChange={(e) => set("landmark", e.currentTarget.value || undefined)}
				/>
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
				<Textarea
					label={t("createListing.addressLabel")}
					placeholder={t("createListing.addressPlaceholder")}
					readOnly
					autosize
					minRows={2}
					maxRows={4}
					value={form.values.address || ""}
					styles={{ input: { backgroundColor: "#f8f9fa", cursor: "default" } }}
				/>
			</FormSection>

			{/* ── Additional Info + Seller Type ── */}
			<FormSection title={t("createListing.additionalInfo")} bg={sectionBg}>
				<Box>
					<Textarea
						label={t("createListing.descriptionLabel")}
						placeholder={t("createListing.descriptionPlaceholder")}
						maxLength={500}
						{...form.getInputProps("description")}
						autosize
						minRows={3}
						maxRows={8}
						styles={{ input: { minHeight: 80 } }}
					/>
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
								(form.values.description?.length ?? 0) >= 500 ? "red" : "dimmed"
							}
						>
							{form.values.description?.length ?? 0} / 500
						</Text>
					</Box>
				</Box>
			</FormSection>

			{/* ── Price ── */}
			<FormSection title={t("createListing.priceSection")} bg={sectionBg}>
				<Box>
					<Switch
						label={t("createListing.negotiable")}
						checked={form.values.is_negotiable}
						onChange={(e) => set("is_negotiable", e.currentTarget.checked)}
						mb={10}
						styles={{ label: { fontWeight: 500, fontSize: 14 } }}
					/>
					{!form.values.is_negotiable && (
						<NumberInput
							label={t("createListing.priceLabel")}
							required
							min={0}
							allowNegative={false}
							allowDecimal={false}
							thousandSeparator=" "
							inputMode="decimal"
							hideControls
							error={form.errors.price}
							{...form.getInputProps("price")}
						/>
					)}
				</Box>
				<ChipSelect
					label={t("createListing.currencyLabel")}
					options={currencyOpts}
					value={form.values.currency}
					onChange={(val) => set("currency", (val as "USD" | "UZS") || "USD")}
				/>
				{/* S3 — urgent_flag (always-visible, defaults to false). */}
				<Switch
					label={t("createListing.urgentFlag")}
					description={t("createListing.urgentFlagDescription")}
					checked={form.values.urgent_flag}
					onChange={(e) => set("urgent_flag", e.currentTarget.checked)}
					styles={{ label: { fontWeight: 500, fontSize: 14 } }}
				/>
			</FormSection>

			{/* ── Contact ── */}
			<FormSection title={t("createListing.contactSection")} bg={sectionBg}>
				<ChipSelect
					label={t("createListing.sellerTypeLabel")}
					options={[
						{ value: "owner", label: t("createListing.sellerTypeOwner") },
						{ value: "realtor", label: t("createListing.sellerTypeRealtor") },
						// S3 (T-001): developer joins the enum.
						{
							value: "developer",
							label: t("createListing.sellerTypeDeveloper"),
						},
					]}
					value={form.values.seller_type}
					onChange={(val) => set("seller_type", (val as string) || "")}
				/>
				{verifiedPhones.length > 1 && (
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
						data={verifiedPhones.map((p) => ({
							value: p.phone,
							label: p.is_primary
								? `${p.phone} (${t("phones.primaryBadge", { defaultValue: "Основной" })})`
								: p.phone,
						}))}
						value={
							verifiedPhones.some((p) => p.phone === form.values.phone)
								? form.values.phone
								: null
						}
						onChange={(val) => set("phone", val || "")}
						clearable={false}
					/>
				)}
				<PhoneInput
					label={t("createListing.phoneLabel")}
					placeholder="+998 XX XXX XX XX"
					description={t("createListing.phoneDescription")}
					value={form.values.phone}
					onChange={(val) => set("phone", val)}
					error={form.errors.phone as string}
				/>
				{/* S3 — seller_telegram (always-visible, optional). */}
				<TextInput
					label={t("createListing.sellerTelegramLabel")}
					placeholder={t("createListing.sellerTelegramPlaceholder")}
					value={form.values.seller_telegram || ""}
					onChange={(e) =>
						set("seller_telegram", e.currentTarget.value || undefined)
					}
				/>
			</FormSection>
		</>
	);
}
