import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Stack,
	Text,
	Group,
	MultiSelect,
	Chip,
	RangeSlider,
	Box,
	Container,
} from "@mantine/core";
import {
	IconTags,
	IconBuildingEstate,
	IconDoor,
	IconCash,
	IconMapPin,
} from "@tabler/icons-react";
import { ROOMS_OPTIONS_KEYS } from "@shared/lib/constants";
import {
	getRegionKeys,
	getDistrictsForRegion,
	translateRegion,
	translateDistrict,
} from "@shared/lib/regions";
import { PreferenceCard } from "./PreferenceCard";
import { ListingTypeSelector } from "./ListingTypeSelector";
import { PropertyTypeSelector } from "./PropertyTypeSelector";
import { $preferences, savePreferencesFx } from "../model";

interface PreferencesPanelProps {
	onDone?: () => void;
}

export function PreferencesPanel(_props: PreferencesPanelProps = {}) {
	const { t } = useTranslation("buyer");
	const saved = useUnit($preferences);

	// Local form state
	const [listingTypes, setListingTypes] = useState<string[]>([]);
	const [propertyTypes, setPropertyTypes] = useState<string[]>([]);
	const [rooms, setRooms] = useState<string[]>([]);
	const [regions, setRegions] = useState<string[]>([]);
	const [districts, setDistricts] = useState<string[]>([]);
	const [priceRange, setPriceRange] = useState<[number, number]>([0, 500000]);
	const initializedRef = useRef(false);
	const debounceRef = useRef<ReturnType<typeof setTimeout>>();
	const pendingSaveRef = useRef<(() => void) | null>(null);

	// Sync from saved preferences on mount
	useEffect(() => {
		if (saved && !initializedRef.current) {
			initializedRef.current = true;
			setListingTypes(saved.listing_types);
			setPropertyTypes(saved.property_types);
			setRooms(saved.rooms.map(String));
			setRegions(saved.regions);
			setDistricts(saved.districts);
			setPriceRange([saved.price_min ?? 0, saved.price_max ?? 500000]);
		}
	}, [saved]);

	// Build save function and keep latest ref for flush-on-unmount
	const doSave = useCallback(() => {
		const isRentOnly =
			listingTypes.includes("rent") && !listingTypes.includes("sell");
		const max = isRentOnly ? 5000 : 500000;
		savePreferencesFx({
			regions,
			districts,
			property_types: propertyTypes,
			listing_types: listingTypes,
			price_min: priceRange[0] > 0 ? priceRange[0] : null,
			price_max: priceRange[1] < max ? priceRange[1] : null,
			rooms: rooms.map((v) => (v === "0" ? 0 : parseInt(v))),
		});
	}, [listingTypes, propertyTypes, rooms, regions, districts, priceRange]);

	// Auto-save with debounce
	const autoSave = useCallback(() => {
		if (!initializedRef.current) return;
		if (debounceRef.current) clearTimeout(debounceRef.current);
		pendingSaveRef.current = doSave;
		debounceRef.current = setTimeout(() => {
			pendingSaveRef.current = null;
			doSave();
		}, 500);
	}, [doSave]);

	// Trigger auto-save when any field changes (skip initial sync)
	useEffect(() => {
		autoSave();
	}, [autoSave]);

	// Flush pending save on unmount (when drawer closes)
	useEffect(() => {
		return () => {
			if (debounceRef.current) clearTimeout(debounceRef.current);
			if (pendingSaveRef.current) pendingSaveRef.current();
		};
	}, []);

	// Districts available based on selected regions
	const availableDistricts = useMemo(() => {
		if (regions.length === 0) return [];
		return regions.flatMap((regionKey) =>
			getDistrictsForRegion(regionKey).map((key) => ({
				value: key,
				label: translateDistrict(key, t),
			})),
		);
	}, [regions, t]);

	// Handle region change: update regions and cascade-clean districts
	const handleRegionsChange = useCallback((newRegions: string[]) => {
		setRegions(newRegions);
		if (newRegions.length === 0) {
			setDistricts([]);
		} else {
			const validKeys = new Set(
				newRegions.flatMap((r) => getDistrictsForRegion(r)),
			);
			setDistricts((prev) => prev.filter((d) => validKeys.has(d)));
		}
	}, []);

	const isRent =
		listingTypes.includes("rent") && !listingTypes.includes("sell");
	const maxPrice = isRent ? 5000 : 500000;
	const priceStep = isRent ? 100 : 5000;

	const propertyTypeLabels: Record<string, string> = {
		apartment: t("common.propertyType.apartment"),
		house: t("common.propertyType.house"),
		commercial: t("common.propertyType.commercial"),
		land: t("common.propertyType.land"),
	};

	return (
		<Container size="sm" px="md" style={{ paddingBottom: 24 }}>
			<Stack gap="md">
				{/* Subtitle */}
				<Text size="sm" c="dimmed" ta="center">
					{t("preferences.subtitle")}
				</Text>

				{/* Listing type */}
				<PreferenceCard
					icon={IconTags}
					iconColor="#228be6"
					iconBg="#e7f5ff"
					title={t("preferences.listingType")}
					description={t("preferences.desc.listingType")}
				>
					<ListingTypeSelector
						value={listingTypes}
						onChange={setListingTypes}
						buyLabel={t("common.buy")}
						rentLabel={t("common.rentAction")}
					/>
				</PreferenceCard>

				{/* Property type */}
				<PreferenceCard
					icon={IconBuildingEstate}
					iconColor="#40c057"
					iconBg="#ebfbee"
					title={t("preferences.propertyType")}
					description={t("preferences.desc.propertyType")}
				>
					<PropertyTypeSelector
						value={propertyTypes}
						onChange={setPropertyTypes}
						labels={propertyTypeLabels}
					/>
				</PreferenceCard>

				{/* Rooms */}
				<PreferenceCard
					icon={IconDoor}
					iconColor="#ff922b"
					iconBg="#fff4e6"
					title={t("preferences.rooms")}
					description={t("preferences.desc.rooms")}
				>
					<Chip.Group multiple value={rooms} onChange={setRooms}>
						<Group gap={8}>
							{ROOMS_OPTIONS_KEYS.map((room) => {
								const val = room === "studio" ? "0" : room;
								const isActive = rooms.includes(val);
								return (
									<Chip
										key={room}
										value={val}
										color="blue"
										variant="light"
										styles={{
											iconWrapper: { display: "none" },
											label: {
												borderRadius: 12,
												fontWeight: 600,
												fontSize: 13,
												padding: "8px 16px",
												height: 38,
												display: "flex",
												alignItems: "center",
												border: isActive
													? "1.5px solid #228be6"
													: "1.5px solid #e9ecef",
											},
										}}
									>
										{room === "studio" ? t("common.roomsOption.studio") : room}
									</Chip>
								);
							})}
						</Group>
					</Chip.Group>
				</PreferenceCard>

				{/* Price Range */}
				<PreferenceCard
					icon={IconCash}
					iconColor="#be4bdb"
					iconBg="#f3f0ff"
					title={t("preferences.priceRange")}
					description={t("preferences.desc.priceRange")}
				>
					<Group justify="center" mb={12}>
						<Box
							style={{
								backgroundColor: "#f3f0ff",
								borderRadius: 10,
								padding: "6px 16px",
							}}
						>
							<Text size="sm" fw={700} c="violet.7">
								${priceRange[0].toLocaleString("ru-RU")} — $
								{priceRange[1].toLocaleString("ru-RU")}
							</Text>
						</Box>
					</Group>
					<Box px={8}>
						<RangeSlider
							color="violet"
							min={0}
							max={maxPrice}
							step={priceStep}
							value={priceRange}
							onChange={(v) => setPriceRange(v as [number, number])}
							marks={
								isRent
									? [
											{ value: 0, label: "$0" },
											{ value: 2500, label: "$2.5k" },
											{ value: 5000, label: "$5k" },
										]
									: [
											{ value: 0, label: "$0" },
											{ value: 250000, label: "$250k" },
											{ value: 500000, label: "$500k" },
										]
							}
							labelAlwaysOn={false}
							mb={24}
						/>
					</Box>
				</PreferenceCard>

				{/* Region & Districts */}
				<PreferenceCard
					icon={IconMapPin}
					iconColor="#e64980"
					iconBg="#fff0f6"
					title={t("preferences.region")}
					description={t("preferences.desc.region")}
				>
					<MultiSelect
						placeholder={t("home.allRegions")}
						value={regions}
						onChange={handleRegionsChange}
						data={getRegionKeys().map((key) => ({
							value: key,
							label: translateRegion(key, t),
						}))}
						clearable
						searchable
						comboboxProps={{ zIndex: 10002 }}
						styles={{ input: { borderRadius: 12 } }}
					/>
					<MultiSelect
						label={t("home.district")}
						placeholder={t("home.allDistricts")}
						value={districts}
						onChange={setDistricts}
						data={availableDistricts}
						disabled={regions.length === 0}
						clearable
						searchable
						comboboxProps={{ zIndex: 10002 }}
						styles={{ input: { borderRadius: 12 } }}
						mt="sm"
					/>
				</PreferenceCard>
			</Stack>
		</Container>
	);
}
