import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
	Box,
	Container,
	TextInput,
	SegmentedControl,
	Button,
	Group,
	Stack,
	Select,
	RangeSlider,
	Text,
	Chip,
	ActionIcon,
	UnstyledButton,
} from "@mantine/core";
import {
	IconSearch,
	IconX,
	IconBuildingSkyscraper,
	IconHome2,
	IconBuildingCommunity,
	IconTrees,
} from "@tabler/icons-react";
import type { ListingFilters } from "@shared/api/types";
import { ROOMS_OPTIONS_KEYS } from "@shared/lib/constants";
import { gradients, shadows, transitions, radii, surface } from "@app/styles/theme";
import {
	getRegionKeys,
	getDistrictsForRegion,
	translateRegion,
	translateDistrict,
} from "@shared/lib/regions";
import { GradientHeader } from "@shared/ui/GradientHeader";
import { FormSection } from "@shared/ui/FormSection";

const PROPERTY_TYPES = [
	{
		value: "apartment",
		labelKey: "common.propertyType.apartment",
		icon: IconBuildingSkyscraper,
		color: "#228be6",
		bg: "#e7f5ff",
	},
	{
		value: "house",
		labelKey: "common.propertyType.house",
		icon: IconHome2,
		color: "#40c057",
		bg: "#ebfbee",
	},
	{
		value: "commercial",
		labelKey: "common.propertyType.commercial",
		icon: IconBuildingCommunity,
		color: "#ff922b",
		bg: "#fff4e6",
	},
	{
		value: "land",
		labelKey: "common.propertyType.land",
		icon: IconTrees,
		color: "#be4bdb",
		bg: "#f3f0ff",
	},
];

const SORT_OPTIONS = [
	"recommended",
	"newest",
	"cheapest",
	"expensive",
] as const;
type SortOption = (typeof SORT_OPTIONS)[number];

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();

	const [searchFocused, setSearchFocused] = useState(false);
	const [sortBy, setSortBy] = useState<SortOption>("recommended");
	const [filters, setFilters] = useState<ListingFilters>({
		type: "sell",
	});
	const [searchQuery, setSearchQuery] = useState("");
	const [priceRange, setPriceRange] = useState<[number, number]>([0, 500000]);
	const [selectedRegion, setSelectedRegion] = useState<string | null>(null);

	const handleSearch = () => {
		const params = new URLSearchParams();

		if (searchQuery.trim()) {
			params.set("q", searchQuery.trim());
		}
		if (filters.type) {
			params.set("type", filters.type);
		}
		if (filters.property_type) {
			params.set("property_type", filters.property_type);
		}
		if (filters.rooms && filters.rooms.length > 0) {
			params.set("rooms", filters.rooms.join(","));
		}
		if (filters.region && filters.region.length > 0) {
			params.set("region", filters.region.join(","));
		}
		if (filters.district && filters.district.length > 0) {
			params.set("district", filters.district.join(","));
		}

		const maxDefault = filters.type === "rent" ? 5000 : 500000;
		if (priceRange[0] > 0) {
			params.set("price_min", String(priceRange[0]));
		}
		if (priceRange[1] < maxDefault) {
			params.set("price_max", String(priceRange[1]));
		}
		if (sortBy !== "recommended") {
			params.set("sort", sortBy);
		}

		const queryString = params.toString();
		navigate(queryString ? `/?${queryString}` : "/");
	};

	const clearFilters = () => {
		setSortBy("recommended");
		setFilters({ type: "sell" });
		setSearchQuery("");
		setPriceRange([0, 500000]);
		setSelectedRegion(null);
	};

	const handleTypeChange = (value: string) => {
		const newMax = value === "rent" ? 5000 : 500000;
		setPriceRange([0, newMax]);
		setFilters({ ...filters, type: value as "sell" | "rent" });
	};

	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			{/* Gradient Header */}
			<GradientHeader icon={IconSearch} title={t("search.title")} />

			{/* Search content */}
			<Container
				size={980}
				px="md"
				style={{
					marginTop: -30,
					position: "relative",
					zIndex: 1,
					paddingBottom: 24,
				}}
			>
				<Stack gap="md">
					{/* Sorting */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: "12px 16px",
							boxShadow: shadows.md,
						}}
					>
						<Text size="sm" fw={600} mb={8} c="gray.7">
							{t("search.sortBy")}
						</Text>
						<Chip.Group
							multiple={false}
							value={sortBy}
							onChange={(value) => setSortBy(value as SortOption)}
						>
							<Group gap={8} wrap="wrap">
								{SORT_OPTIONS.map((option) => (
									<Chip
										key={option}
										value={option}
										variant="filled"
										radius={17}
										styles={{
											label: {
												height: 34,
												padding: "0 17px",
												fontSize: 12,
												fontWeight: 600,
												backgroundColor:
													sortBy === option ? "#FF6E01" : "#F1F1F1",
												color: sortBy === option ? "#FFFFFF" : "#9F9F9F",
												border: "none",
											},
											iconWrapper: { display: "none" },
										}}
									>
										{t(`search.sort.${option}`)}
									</Chip>
								))}
							</Group>
						</Chip.Group>
					</Box>

					{/* Search Input Card */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: "12px 16px",
							boxShadow: shadows.md,
						}}
					>
						<TextInput
							placeholder={searchFocused ? "" : t("search.title")}
							leftSection={<IconSearch size={18} color="#adb5bd" />}
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.currentTarget.value)}
							onKeyDown={(e) => e.key === "Enter" && handleSearch()}
							onFocus={() => setSearchFocused(true)}
							onBlur={() => setSearchFocused(false)}
							rightSection={
								searchQuery ? (
									<ActionIcon
										variant="filled"
										size={18}
										radius="50%"
										color="gray.5"
										onMouseDown={(e) => e.preventDefault()}
										onClick={() => setSearchQuery("")}
									>
										<IconX size={10} color="white" />
									</ActionIcon>
								) : null
							}
							radius={22}
							styles={{
								input: {
									backgroundColor: searchFocused ? "#f8f9fa" : "#f1f3f5",
									border: searchFocused ? "1px solid #dee2e6" : "none",
									height: 45,
									fontSize: 16,
									transition:
										"background-color 0.15s ease, border-color 0.15s ease",
								},
							}}
						/>
					</Box>

					{/* Deal Type */}
					<FormSection title={t("common.buy") + " / " + t("common.rentAction")}>
						<SegmentedControl
							fullWidth
							value={filters.type || "sell"}
							onChange={handleTypeChange}
							data={[
								{ label: t("common.buy"), value: "sell" },
								{ label: t("common.rentAction"), value: "rent" },
							]}
							styles={{
								root: {
									backgroundColor: "#f1f3f5",
									borderRadius: radii.md,
									padding: 4,
								},
								label: { fontWeight: 600, fontSize: 14 },
								indicator: {
									borderRadius: radii.md,
									boxShadow: shadows.md,
								},
							}}
						/>
					</FormSection>

					{/* Property Type */}
					<FormSection title={t("search.propertyType")}>
						<Group gap={10}>
							{PROPERTY_TYPES.map((pt) => {
								const isSelected = filters.property_type === pt.value;
								return (
									<UnstyledButton
										key={pt.value}
										onClick={() =>
											setFilters({
												...filters,
												property_type: isSelected
													? undefined
													: (pt.value as ListingFilters["property_type"]),
											})
										}
										style={{ flex: 1, minWidth: 0 }}
									>
										<Box
											style={{
												backgroundColor: isSelected ? pt.color : "white",
												borderRadius: radii.lg,
												padding: "14px 8px",
												textAlign: "center",
												boxShadow: isSelected
													? `0 6px 16px ${pt.color}40`
													: shadows.md,
												transition: transitions.spring,
												transform: isSelected ? "translateY(-2px)" : "none",
												border: isSelected
													? `1.5px solid ${pt.color}`
													: "1.5px solid #f1f3f5",
											}}
										>
											<Box
												style={{
													width: 40,
													height: 40,
													borderRadius: radii.md,
													backgroundColor: isSelected
														? "rgba(255,255,255,0.25)"
														: pt.bg,
													display: "flex",
													alignItems: "center",
													justifyContent: "center",
													margin: "0 auto 6px",
													transition: transitions.fast,
												}}
											>
												<pt.icon
													size={20}
													color={isSelected ? "white" : pt.color}
													stroke={2}
												/>
											</Box>
											<Text
												size="10px"
												fw={600}
												c={isSelected ? "white" : "gray.7"}
												style={{ lineHeight: 1.2 }}
											>
												{t(pt.labelKey)}
											</Text>
										</Box>
									</UnstyledButton>
								);
							})}
						</Group>
					</FormSection>

					{/* Rooms */}
					<FormSection title={t("search.roomsCount")}>
						<Chip.Group
							multiple
							value={filters.rooms?.map(String) || []}
							onChange={(values) =>
								setFilters({
									...filters,
									rooms: values.map((v) => (v === "0" ? 0 : parseInt(v))),
								})
							}
						>
							<Group gap={8}>
								{ROOMS_OPTIONS_KEYS.map((room) => (
									<Chip
										key={room}
										value={room === "studio" ? "0" : room}
										styles={{
											iconWrapper: { display: "none" },
											label: {
												borderRadius: 20,
												fontWeight: 600,
												fontSize: 13,
												padding: "8px 18px",
												boxShadow: shadows.md,
												transition: transitions.fast,
											},
										}}
									>
										{room === "studio" ? t("common.roomsOption.studio") : room}
									</Chip>
								))}
							</Group>
						</Chip.Group>
					</FormSection>

					{/* Price Range */}
					<FormSection
						title={t("search.price", {
							unit:
								filters.type === "rent"
									? t("home.priceUnitRent")
									: t("home.priceUnitSell"),
						})}
					>
						<Group justify="flex-end" mb={8}>
							<Box
								style={{
									backgroundColor: "#e7f5ff",
									borderRadius: radii.sm,
									padding: "4px 12px",
								}}
							>
								<Text size="sm" fw={700} c="blue">
									${priceRange[0].toLocaleString("ru-RU")} — $
									{priceRange[1].toLocaleString("ru-RU")}
								</Text>
							</Box>
						</Group>
						<Box px={8}>
							<RangeSlider
								min={0}
								max={filters.type === "rent" ? 5000 : 500000}
								step={filters.type === "rent" ? 100 : 5000}
								value={priceRange}
								onChange={setPriceRange}
								marks={
									filters.type === "rent"
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
								label={(value) =>
									value >= 1000 ? `$${(value / 1000).toFixed(0)}k` : `$${value}`
								}
								mb={24}
								styles={{
									track: {
										height: 6,
										borderRadius: 3,
										backgroundColor: "#e9ecef",
									},
									bar: {
										backgroundColor: "#228be6",
										borderRadius: 3,
									},
									thumb: {
										width: 22,
										height: 22,
										backgroundColor: surface.card,
										borderWidth: 3,
										borderColor: "#228be6",
										boxShadow: shadows.accent,
									},
									markLabel: {
										fontSize: 12,
										color: "#868e96",
										marginTop: 8,
									},
									label: {
										backgroundColor: "#228be6",
										fontSize: 11,
										fontWeight: 600,
										padding: "2px 8px",
										borderRadius: 6,
									},
								}}
							/>
						</Box>
					</FormSection>

					{/* Location */}
					<FormSection title={t("search.region")}>
						<Select
							label={t("search.region")}
							placeholder={t("search.allRegions")}
							value={selectedRegion}
							onChange={(value) => {
								setSelectedRegion(value);
								setFilters({
									...filters,
									region: value ? [value] : undefined,
									district: undefined,
								});
							}}
							data={getRegionKeys().map((key) => ({
								value: key,
								label: translateRegion(key, t),
							}))}
							clearable
							searchable
							styles={{ input: { borderRadius: 12 } }}
						/>
						<Select
							label={t("search.district")}
							placeholder={t("search.allDistricts")}
							value={filters.district?.[0] || null}
							onChange={(value) =>
								setFilters({
									...filters,
									district: value ? [value] : undefined,
								})
							}
							data={
								selectedRegion
									? getDistrictsForRegion(selectedRegion).map((key) => ({
											value: key,
											label: translateDistrict(key, t),
										}))
									: []
							}
							disabled={!selectedRegion}
							clearable
							searchable
							styles={{ input: { borderRadius: 12 } }}
						/>
					</FormSection>

					{/* Spacer for sticky buttons + bottom nav */}
					<Box style={{ height: 140 }} />
				</Stack>
			</Container>

			{/* Sticky Action Buttons */}
			<Box
				style={{
					position: "fixed",
					bottom: 68,
					left: 0,
					right: 0,
					padding: "12px 16px",
					backgroundColor: "rgba(255,255,255,0.95)",
					backdropFilter: "blur(10px)",
					WebkitBackdropFilter: "blur(10px)",
					borderTop: "1px solid rgba(0,0,0,0.06)",
					zIndex: 999,
				}}
			>
				<Group grow>
					<Button
						variant="light"
						onClick={clearFilters}
						radius="xl"
						size="md"
						style={{ height: 48 }}
					>
						{t("search.reset")}
					</Button>
					<Button
						onClick={handleSearch}
						radius="xl"
						size="md"
						style={{
							height: 48,
							background: gradients.primary,
							border: "none",
							boxShadow: shadows.accent,
							fontWeight: 700,
						}}
					>
						{t("search.find")}
					</Button>
				</Group>
			</Box>
		</Box>
	);
}

export const Search = {
	route: "/search",
	Page,
};
