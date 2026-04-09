import {
	Textarea,
	NumberInput,
	Box,
	Text,
	Switch,
} from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Suspense, lazy, useMemo } from "react";
import { FormSection } from "@shared/ui/FormSection";
import { ChipSelect } from "@shared/ui/ChipSelect";
import { ChipMultiSelect } from "@shared/ui/ChipMultiSelect";
import { PhoneInput } from "@shared/ui/PhoneInput";
import { resolveLocationCoords } from "@shared/constants/locationCoords";
import type { UseFormReturnType } from "@mantine/form";
import type { ListingFormValues } from "./useListingForm";

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

// ── Visibility helpers (spec Section 3) ──
function vis(pt: string) {
	const isApt = pt === "apartment";
	const isHouse = pt === "house";
	const isCom = pt === "commercial";
	const isLand = pt === "land";
	return {
		// Core
		rooms: isApt || isHouse,
		area: !isLand,
		livingArea: isApt || isHouse,
		kitchenArea: isApt,
		landArea: isHouse || isLand,
		floor: isApt || isCom,
		totalFloors: isApt || isCom,
		ceilingHeight: !isLand,
		// Apartment-only
		buildingType: isApt,
		condition: isApt || isCom,
		layout: isApt,
		// House-only
		houseType: isHouse,
		houseCondition: isHouse,
		locationType: isHouse,
		utilities: isHouse,
		// Common
		buildingMaterial: isApt || isHouse,
		bathroom: isApt || isHouse,
		furnished: !isLand,
		// Amenities
		aptAmenities: isApt,
		houseAmenities: isHouse,
		nearbyAmenities: !isLand,
		// Land
		landPurpose: isLand,
	};
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
	const show = vis(pt);

	const locationCenter = useMemo(
		() =>
			resolveLocationCoords(
				form.values.region || null,
				form.values.district || null,
			),
		[form.values.region, form.values.district],
	);

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
	const conditionOpts = [
		{ value: "euro", label: t("createListing.condEuro") },
		{ value: "cosmetic", label: t("createListing.condCosmetic") },
		{ value: "needs_repair", label: t("createListing.condRepair") },
		{ value: "rough", label: t("createListing.condRough") },
		{ value: "none", label: t("createListing.condNone") },
	];

	const furnishedOpts = [
		{ value: "yes", label: t("createListing.yes") },
		{ value: "no", label: t("createListing.no") },
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

	const landPurposeOpts = [
		{ value: "private", label: t("createListing.lpPrivate") },
		{ value: "industrial", label: t("createListing.lpIndustrial") },
		{ value: "agricultural", label: t("createListing.lpAgri") },
		{ value: "commercial", label: t("createListing.lpCommercial") },
	];

	const currencyOpts = [
		{ value: "USD", label: t("createListing.currencyUSD") },
		{ value: "UZS", label: t("createListing.currencyUZS") },
	];

	const set = (key: string, val: any) => form.setFieldValue(key, val);

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
						const newPt =
							(val as ListingFormValues["property_type"]) || "apartment";
						set("property_type", newPt);
						// Land: force sell, clear inapplicable
						if (newPt === "land") {
							set("type", "sell");
							set("rooms", undefined);
							set("floor", undefined);
							set("amenities", []);
							set("nearby_amenities", []);
						}
						// Clear apartment-specific fields when leaving apartment
						if (newPt !== "apartment") {
							set("building_type", undefined);
							set("condition", undefined);
							set("kitchen_area", undefined);
						}
						// Clear house-specific fields when leaving house
						if (newPt !== "house") {
							set("house_type", undefined);
							set("house_condition", []);
							set("location_type", []);
							set("water_supply", []);
							set("electricity", undefined);
							set("heating", []);
							set("gas_supply", undefined);
							set("sewage", undefined);
						}
						// Clear land-specific when leaving land/house
						if (newPt !== "land" && newPt !== "house") {
							set("land_area", undefined);
							set("land_purpose", undefined);
						}
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
						onChange={(val) => set("type", (val as string) || "sell")}
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

			{/* ── Apartment Attributes ── */}
			{(show.buildingType || show.condition || show.furnished) && (
				<FormSection title={t("createListing.aptAttributes")} bg={sectionBg}>
					{show.buildingType && (
						<ChipSelect
							label={t("createListing.buildingType")}
							required
							options={[
								{ value: "new", label: t("createListing.buildingNew") },
								{
									value: "secondary",
									label: t("createListing.buildingSecondary"),
								},
							]}
							value={form.values.building_type}
							onChange={(val) =>
								set("building_type", val as string | undefined)
							}
							error={form.errors.building_type as string}
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
					{show.furnished && (
						<ChipSelect
							label={t("createListing.furnished")}
							required
							options={furnishedOpts}
							value={form.values.is_furnished}
							onChange={(val) => set("is_furnished", val as string | undefined)}
							error={form.errors.is_furnished as string}
						/>
					)}
				</FormSection>
			)}

			{/* ── House-Specific Attributes ── */}
			{show.houseType && (
				<FormSection title={t("createListing.houseAttributes")} bg={sectionBg}>
					<ChipSelect
						label={t("createListing.houseType")}
						options={houseTypeOpts}
						value={form.values.house_type}
						onChange={(val) => set("house_type", val as string | undefined)}
					/>
					<ChipMultiSelect
						label={t("createListing.houseCondition")}
						description={t("createListing.multipleAllowed")}
						options={houseConditionOpts}
						value={form.values.house_condition}
						onChange={(val) => set("house_condition", val)}
					/>
					<ChipMultiSelect
						label={t("createListing.locationType")}
						description={t("createListing.multipleAllowed")}
						options={locationTypeOpts}
						value={form.values.location_type}
						onChange={(val) => set("location_type", val)}
					/>
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

			{/* ── Land Purpose (Land only) ── */}
			{show.landPurpose && (
				<FormSection title={t("createListing.landPurposeSection")} bg={sectionBg}>
					<ChipSelect
						label={t("createListing.landPurpose")}
						options={landPurposeOpts}
						value={form.values.land_purpose}
						onChange={(val) => set("land_purpose", val as string | undefined)}
					/>
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
						onRegionChange(val ? String(val) : "");
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
						maxLength={100}
						{...form.getInputProps("description")}
						styles={{ input: { minHeight: 100 } }}
					/>
					<Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
						<Text size="xs" c={(form.values.description?.length ?? 0) >= 100 ? "red" : "transparent"}>
							{t("createListing.charLimitReached", { count: 100 })}
						</Text>
						<Text size="xs" c={(form.values.description?.length ?? 0) >= 100 ? "red" : "dimmed"}>
							{form.values.description?.length ?? 0} / 100
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
			</FormSection>

			{/* ── Contact ── */}
			<FormSection title={t("createListing.contactSection")} bg={sectionBg}>
				<ChipSelect
					label={t("createListing.sellerTypeLabel")}
					options={[
						{ value: "owner", label: t("createListing.sellerTypeOwner") },
						{ value: "realtor", label: t("createListing.sellerTypeRealtor") },
					]}
					value={form.values.seller_type}
					onChange={(val) => set("seller_type", (val as string) || "")}
				/>
				<PhoneInput
					label={t("createListing.phoneLabel")}
					placeholder="+998 XX XXX XX XX"
					description={t("createListing.phoneDescription")}
					value={form.values.phone}
					onChange={(val) => set("phone", val)}
					error={form.errors.phone as string}
				/>
			</FormSection>
		</>
	);
}
