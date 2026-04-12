import { useEffect, useCallback, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Box,
	Container,
	Loader,
	Center,
	Text,
	Stack,
	Skeleton,
	ActionIcon,
	Group,
	Drawer,
	Button,
	Select,
	Chip,
	RangeSlider,
	ScrollArea,
	UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconSearch,
	IconX,
	IconSparkles,
	IconBell,
	IconAdjustments,
	IconArrowsSort,
	IconTags,
	IconBuildingEstate,
	IconDoor,
	IconCash,
	IconMapPin,
	IconKey,
	IconCalendarEvent,
	IconBuildingSkyscraper,
	IconHome2,
	IconBuildingCommunity,
	IconTrees,
} from "@tabler/icons-react";
import { transitions, shadows, radii, surface } from "@app/styles/theme";
import { PreferenceCard } from "@modules/buyer/feature/preferences/ui/PreferenceCard";
import {
	useLayoutContext,
	clearScrollPosition,
} from "@modules/buyer/app/ui/layout/BuyerLayout";
import { ListingCard } from "@shared/ui/ListingCard";
import { useSwipeDismiss } from "@shared/hooks/useSwipeDismiss";
import { RootPage } from "@shared/ui/RootPage";
import {
	getListingDetailUrl,
	type SourcedListingListItem,
} from "@shared/lib/crawlerAdapter";
import { $userStats } from "@shared/state/user/model";
import {
	seedListingIds,
	seedListingSource,
} from "@modules/buyer/shared/state/model";
import { ROOMS_OPTIONS_KEYS } from "@shared/lib/constants";
import {
	getRegionKeys,
	getDistrictsForRegion,
	translateRegion,
	translateDistrict,
} from "@shared/lib/regions";
import {
	$listings,
	$isLoading,
	$hasMore,
	$favoritedIds,
	$searchQuery,
	$filters,
	pageOpened,
	loadMore,
	toggleFavorite,
	searchQueryChanged,
	filtersChanged,
	applyFilters,
	clearFilters,
	type HomeFilters,
} from "../../model";

const QUICK_FILTER_VALUES = [
	"apartment",
	"house",
	"commercial",
	"land",
] as const;

function Page() {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const [
		listings,
		isLoading,
		hasMore,
		favoritedIds,
		searchQuery,
		filters,
		userStats,
	] = useUnit([
		$listings,
		$isLoading,
		$hasMore,
		$favoritedIds,
		$searchQuery,
		$filters,
		$userStats,
	]);
	const observerRef = useRef<IntersectionObserver | null>(null);
	const loadMoreRef = useRef<HTMLDivElement | null>(null);
	const initializedRef = useRef(false);
	const [drawerOpened, { open: openDrawer, close: closeDrawer }] =
		useDisclosure(false);
	const { openSearch, searchOpen } = useLayoutContext();
	const filterScrollRef = useRef<HTMLDivElement>(null);
	const filterSwipe = useSwipeDismiss({
		onClose: closeDrawer,
		threshold: 120,
		resistance: 0.6,
		scrollRef: filterScrollRef,
		enabled: drawerOpened,
	});
	const [sortBy, setSortBy] = useState<string>("recommended");
	const [viewMode] = useState<"grid" | "masonry">("grid");
	const [localPriceRange, setLocalPriceRange] = useState<[number, number]>([
		0, 500000,
	]);
	const [selectedRegion, setSelectedRegion] = useState<string | null>(null);

	useEffect(() => {
		const min = filters.price_min || 0;
		const max = filters.price_max || (filters.type === "rent" ? 5000 : 500000);
		setLocalPriceRange([min, max]);
	}, [filters.price_min, filters.price_max, filters.type]);

	// Initialize from URL params
	useEffect(() => {
		if (initializedRef.current) return;
		initializedRef.current = true;

		const urlFilters: Partial<HomeFilters> = {};
		const q = searchParams.get("q");
		const type = searchParams.get("type") as "sell" | "rent" | null;
		const propertyType = searchParams.get(
			"property_type",
		) as HomeFilters["property_type"];
		const rooms = searchParams.get("rooms");
		const priceMin = searchParams.get("price_min");
		const priceMax = searchParams.get("price_max");
		const region = searchParams.get("region");
		const district = searchParams.get("district");

		if (q) urlFilters.q = q;
		if (type) urlFilters.type = type;
		if (propertyType) urlFilters.property_type = propertyType;
		if (rooms) urlFilters.rooms = rooms.split(",").map(Number);
		if (priceMin) urlFilters.price_min = Number(priceMin);
		if (priceMax) urlFilters.price_max = Number(priceMax);
		if (region) {
			urlFilters.region = region.split(",");
			setSelectedRegion(region.split(",")[0] || null);
		}
		if (district) urlFilters.district = district.split(",");

		const hasUrlFilters = Object.keys(urlFilters).length > 0;
		if (hasUrlFilters) {
			filtersChanged(urlFilters);
		}

		// Skip re-fetch if we already have listings and no new URL filters are being applied.
		// Effector stores survive unmount/remount, so on back-navigation the data is still there.
		if (listings.length > 0 && !hasUrlFilters) {
			return;
		}

		pageOpened();
	}, [searchParams]);

	// Count active filters (excluding search query)
	const activeFilterCount = [
		filters.type,
		filters.property_type,
		filters.rooms?.length,
		filters.price_min,
		filters.price_max,
		filters.region?.length,
		filters.district?.length,
	].filter(Boolean).length;

	const handleCardClick = useCallback(
		(id: string) => {
			seedListingIds(listings.map((l) => l.id));
			seedListingSource("feed");
			const item = listings.find((l) => l.id === id) as
				| SourcedListingListItem
				| undefined;
			if (item) {
				navigate(getListingDetailUrl(item));
			} else {
				navigate(`/listings/${id}`);
			}
		},
		[navigate, listings],
	);

	// Infinite scroll with IntersectionObserver
	useEffect(() => {
		if (observerRef.current) {
			observerRef.current.disconnect();
		}

		observerRef.current = new IntersectionObserver(
			(entries) => {
				if (entries[0].isIntersecting && hasMore && !isLoading) {
					loadMore();
				}
			},
			{ threshold: 0.1 },
		);

		if (loadMoreRef.current) {
			observerRef.current.observe(loadMoreRef.current);
		}

		return () => {
			if (observerRef.current) {
				observerRef.current.disconnect();
			}
		};
	}, [hasMore, isLoading]);

	// Wrapper: any filter/search action that resets the feed should also clear saved scroll
	const applyFiltersAndClearScroll = useCallback(() => {
		clearScrollPosition("/");
		applyFilters();
	}, []);

	const handleClearFilters = () => {
		clearScrollPosition("/");
		clearFilters();
		setSortBy("recommended");
		setLocalPriceRange([0, 500000]);
		setSelectedRegion(null);
		setSearchParams({});
	};

	const handleTypeChange = (value: string) => {
		clearScrollPosition("/");
		const newMax = value === "rent" ? 5000 : 500000;
		setLocalPriceRange([0, newMax]);
		filtersChanged({
			type: value as "sell" | "rent",
			price_min: undefined,
			price_max: undefined,
		});
		applyFiltersAndClearScroll();
	};

	const handleQuickFilter = (propertyType: string) => {
		const isSame = filters.property_type === propertyType;
		filtersChanged({
			property_type: isSame
				? undefined
				: (propertyType as HomeFilters["property_type"]),
		});
		applyFiltersAndClearScroll();
	};

	// Search header content (rendered inside RootPage's TabBar)
	const SearchHeaderContent = (
		<>
			{/* Search bar + notification */}
			<Box px="md" pt="sm" pb={8} style={{ maxWidth: 980, margin: "0 auto" }}>
				<Group gap={8} wrap="nowrap">
					<UnstyledButton
						onClick={openSearch}
						style={{
							flex: 1,
							minWidth: 0,
							height: 46,
							borderRadius: radii.xl,
							backgroundColor: "#ffffff",
							border: "1px solid #ced4da",
							boxShadow: shadows.md,
							display: "flex",
							alignItems: "center",
							paddingLeft: 16,
							paddingRight: 8,
							gap: 10,
						}}
					>
						<IconSearch size={20} color="#adb5bd" />
						<Text
							size="sm"
							c={searchQuery ? "dark" : "dimmed"}
							style={{
								userSelect: "none",
								flex: 1,
								overflow: "hidden",
								textOverflow: "ellipsis",
								whiteSpace: "nowrap",
							}}
						>
							{searchOpen ? "" : searchQuery || t("search.title")}
						</Text>
						{searchQuery && (
							<ActionIcon
								variant="filled"
								size={18}
								radius="50%"
								color="gray.5"
								onClick={(e) => {
									e.stopPropagation();
									clearScrollPosition("/");
									searchQueryChanged("");
									clearFilters();
									setSearchParams(new URLSearchParams());
								}}
							>
								<IconX size={10} color="white" />
							</ActionIcon>
						)}
						<ActionIcon
							variant="subtle"
							color="dark"
							size={32}
							radius="xl"
							onClick={(e) => {
								e.stopPropagation();
								openDrawer();
							}}
						>
							<IconAdjustments
								size={20}
								stroke={1.6}
								style={{ transform: "rotate(90deg)" }}
							/>
						</ActionIcon>
					</UnstyledButton>
					<Box
						style={{ position: "relative", cursor: "pointer" }}
						onClick={() => navigate("/notifications")}
					>
						<ActionIcon variant="subtle" color="gray" size={42} radius="xl">
							<IconBell size={22} stroke={1.6} />
						</ActionIcon>
						{(userStats?.unreadCount ?? 0) > 0 && (
							<Box
								style={{
									position: "absolute",
									top: 2,
									right: 2,
									minWidth: 16,
									height: 16,
									borderRadius: 8,
									backgroundColor: "#ff6b6b",
									border: "2px solid white",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									padding: "0 3px",
								}}
							>
								<Text
									style={{
										fontSize: 9,
										fontWeight: 700,
										color: "white",
										lineHeight: 1,
									}}
								>
									{(userStats?.unreadCount ?? 0) > 99
										? "99+"
										: userStats?.unreadCount}
								</Text>
							</Box>
						)}
					</Box>
				</Group>
			</Box>

			{/* Quick filter chips */}
			<ScrollArea scrollbarSize={0} type="never" offsetScrollbars={false}>
				<Box px="md" pb="sm" style={{ display: "flex", gap: 6, maxWidth: 980, margin: "0 auto" }}>
					{QUICK_FILTER_VALUES.map((value) => {
						const isSelected = filters.property_type === value;
						return (
							<Box
								key={value}
								onClick={() => handleQuickFilter(value)}
								style={{
									padding: "5px 15px",
									borderRadius: radii.full,
									backgroundColor: isSelected ? "#228be6" : "#f1f3f5",
									border: isSelected ? "1px solid #228be6" : "1px solid #ced4da",
									boxShadow: shadows.md,
									cursor: "pointer",
									whiteSpace: "nowrap",
									transition: "all 0.2s ease",
									flexShrink: 0,
									WebkitTapHighlightColor: "transparent",
									outline: "none",
									userSelect: "none",
								}}
							>
								<Text
									size="xs"
									fw={600}
									c={isSelected ? "white" : "gray.7"}
									style={{ lineHeight: 1.3 }}
								>
									{t(`common.propertyTypePlural.${value}`)}
								</Text>
							</Box>
						);
					})}
				</Box>
			</ScrollArea>
		</>
	);

	// Filter drawer
	const filterTransition = filterSwipe.isDragging
		? "none"
		: filterSwipe.isClosing
			? "transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
			: "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";

	const FilterDrawer = (
		<Drawer
			opened={drawerOpened}
			onClose={closeDrawer}
			withCloseButton={false}
			position="bottom"
			size="auto"
			styles={{
				content: {
					borderRadius: "20px 20px 0 0",
					maxHeight: "90vh",
					overflow: "hidden",
					backgroundColor: surface.page,
					maxWidth: 980,
					margin: "0 auto",
				},
				header: { display: "none" },
				body: {
					padding: 0,
					maxHeight: "90vh",
					display: "flex",
					flexDirection: "column",
				},
			}}
		>
			<Box
				{...filterSwipe.handlers}
				style={{
					display: "flex",
					flexDirection: "column",
					maxHeight: "90vh",
					transform: `translateY(${filterSwipe.dragOffset}px)`,
					transition: filterTransition,
				}}
			>
				{/* Drag handle */}
				<Box
					py={10}
					style={{
						display: "flex",
						justifyContent: "center",
						cursor: "grab",
						flexShrink: 0,
					}}
				>
					<Box
						style={{
							width: 36,
							height: 4,
							borderRadius: 2,
							backgroundColor: "#ced4da",
						}}
					/>
				</Box>

				{/* Header */}
				<Box px="md" pb="sm" style={{ flexShrink: 0 }}>
					<Text
						fw={700}
						size="lg"
						style={{ fontFamily: "var(--mantine-font-family-headings)" }}
					>
						{t("home.filters")}
					</Text>
				</Box>

				{/* Scrollable content */}
				<Box
					ref={filterScrollRef}
					style={{
						flex: 1,
						overflowY: "auto",
						overflowX: "hidden",
						scrollbarWidth: "none",
						msOverflowStyle: "none",
						WebkitOverflowScrolling: "touch",
					}}
				>
					<Stack gap="md" pb={80} px="md">
						{/* Sorting */}
						<PreferenceCard
							icon={IconArrowsSort}
							iconColor="#FF6E01"
							iconBg="#FFF4E6"
							title={t("search.sortBy")}
						>
							<Chip.Group
								multiple={false}
								value={sortBy}
								onChange={(value) => setSortBy(value as string)}
							>
								<Group gap={8} wrap="wrap">
									{(
										["recommended", "newest", "cheapest", "expensive"] as const
									).map((option) => (
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
						</PreferenceCard>

						{/* Deal type */}
						<PreferenceCard
							icon={IconTags}
							iconColor="#228be6"
							iconBg="#e7f5ff"
							title={t("preferences.listingType")}
							description={t("preferences.desc.listingType")}
						>
							<Group grow gap={10}>
								{(
									[
										{
											value: "sell",
											icon: IconKey,
											color: "#228be6",
											bg: "#e7f5ff",
											label: t("common.buy"),
										},
										{
											value: "rent",
											icon: IconCalendarEvent,
											color: "#40c057",
											bg: "#ebfbee",
											label: t("common.rentAction"),
										},
									] as const
								).map(({ value, icon: Icon, color, bg, label }) => {
									const selected = filters.type === value;
									return (
										<UnstyledButton
											key={value}
											onClick={() => handleTypeChange(value)}
										>
											<Box
												style={{
													backgroundColor: selected ? bg : surface.page,
													borderRadius: radii.md,
													padding: "18px 12px",
													textAlign: "center",
													border: selected
														? `2px solid ${color}`
														: "2px solid #e9ecef",
													transition: transitions.spring,
													transform: selected ? "translateY(-1px)" : "none",
													boxShadow: selected
														? `0 4px 12px ${color}25`
														: "none",
												}}
											>
												<Box
													style={{
														width: 48,
														height: 48,
														borderRadius: radii.md,
														backgroundColor: selected ? `${color}20` : "white",
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														margin: "0 auto 10px",
														transition: transitions.fast,
													}}
												>
													<Icon size={24} color={color} stroke={1.8} />
												</Box>
												<Text
													size="sm"
													fw={600}
													c={selected ? color : "gray.7"}
												>
													{label}
												</Text>
											</Box>
										</UnstyledButton>
									);
								})}
							</Group>
						</PreferenceCard>

						{/* Property type */}
						<PreferenceCard
							icon={IconBuildingEstate}
							iconColor="#40c057"
							iconBg="#ebfbee"
							title={t("preferences.propertyType")}
							description={t("preferences.desc.propertyType")}
						>
							<Group grow gap={10}>
								{(
									[
										{
											value: "apartment",
											icon: IconBuildingSkyscraper,
											color: "#228be6",
											bg: "#e7f5ff",
										},
										{
											value: "house",
											icon: IconHome2,
											color: "#40c057",
											bg: "#ebfbee",
										},
										{
											value: "commercial",
											icon: IconBuildingCommunity,
											color: "#ff922b",
											bg: "#fff4e6",
										},
										{
											value: "land",
											icon: IconTrees,
											color: "#be4bdb",
											bg: "#f3f0ff",
										},
									] as const
								).map(({ value, icon: Icon, color, bg }) => {
									const selected = filters.property_type === value;
									return (
										<UnstyledButton
											key={value}
											onClick={() => {
												filtersChanged({
													property_type: selected
														? undefined
														: (value as HomeFilters["property_type"]),
												});
												applyFiltersAndClearScroll();
											}}
										>
											<Box
												style={{
													backgroundColor: selected ? bg : surface.page,
													borderRadius: radii.md,
													padding: "14px 4px 12px",
													textAlign: "center",
													border: selected
														? `2px solid ${color}`
														: "2px solid transparent",
													transition: transitions.spring,
													transform: selected ? "translateY(-1px)" : "none",
													boxShadow: selected
														? `0 4px 12px ${color}20`
														: "0 1px 3px rgba(0,0,0,0.04)",
												}}
											>
												<Box
													style={{
														width: 40,
														height: 40,
														borderRadius: radii.md,
														backgroundColor: selected ? `${color}20` : "white",
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														margin: "0 auto 8px",
														transition: transitions.fast,
													}}
												>
													<Icon size={20} color={color} stroke={1.8} />
												</Box>
												<Text
													size="10px"
													fw={600}
													c={selected ? color : "gray.7"}
													lh={1.2}
												>
													{t(`common.propertyType.${value}`)}
												</Text>
											</Box>
										</UnstyledButton>
									);
								})}
							</Group>
						</PreferenceCard>

						{/* Rooms */}
						<PreferenceCard
							icon={IconDoor}
							iconColor="#ff922b"
							iconBg="#fff4e6"
							title={t("preferences.rooms")}
							description={t("preferences.desc.rooms")}
						>
							<Chip.Group
								multiple
								value={filters.rooms?.map(String) || []}
								onChange={(values) => {
									filtersChanged({
										rooms:
											values.length > 0
												? values.map((v) => (v === "0" ? 0 : parseInt(v)))
												: undefined,
									});
									applyFiltersAndClearScroll();
								}}
							>
								<Group gap={8}>
									{ROOMS_OPTIONS_KEYS.map((room) => {
										const val = room === "studio" ? "0" : room;
										const isActive = (
											filters.rooms?.map(String) || []
										).includes(val);
										return (
											<Chip
												key={room}
												value={val}
												color="blue"
												variant="light"
												styles={{
													iconWrapper: { display: "none" },
													label: {
														borderRadius: radii.md,
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
												{room === "studio"
													? t("common.roomsOption.studio")
													: room}
											</Chip>
										);
									})}
								</Group>
							</Chip.Group>
						</PreferenceCard>

						{/* Price range */}
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
										borderRadius: radii.md,
										padding: "6px 16px",
									}}
								>
									<Text size="sm" fw={700} c="violet.7">
										${localPriceRange[0].toLocaleString("ru-RU")} — $
										{localPriceRange[1].toLocaleString("ru-RU")}
									</Text>
								</Box>
							</Group>
							<Box px={8}>
								<RangeSlider
									color="violet"
									min={0}
									max={filters.type === "rent" ? 5000 : 500000}
									step={filters.type === "rent" ? 100 : 5000}
									value={localPriceRange}
									onChange={(value) =>
										setLocalPriceRange(value as [number, number])
									}
									onChangeEnd={(value) => {
										const maxDefault = filters.type === "rent" ? 5000 : 500000;
										filtersChanged({
											price_min: value[0] > 0 ? value[0] : undefined,
											price_max: value[1] < maxDefault ? value[1] : undefined,
										});
										applyFiltersAndClearScroll();
									}}
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
									mb={24}
								/>
							</Box>
						</PreferenceCard>

						{/* Region & District */}
						<PreferenceCard
							icon={IconMapPin}
							iconColor="#e64980"
							iconBg="#fff0f6"
							title={t("preferences.region")}
							description={t("preferences.desc.region")}
						>
							<Select
								placeholder={t("home.allRegions")}
								value={selectedRegion}
								onChange={(value) => {
									setSelectedRegion(value);
									filtersChanged({
										region: value ? [value] : undefined,
										district: undefined,
									});
									applyFiltersAndClearScroll();
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
								label={t("home.district")}
								placeholder={t("home.allDistricts")}
								value={filters.district?.[0] || null}
								onChange={(value) => {
									filtersChanged({ district: value ? [value] : undefined });
									applyFiltersAndClearScroll();
								}}
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
								mt="sm"
							/>
						</PreferenceCard>

						{/* Clear filters */}
						<Button
							variant="light"
							onClick={handleClearFilters}
							radius={12}
							size="md"
							fullWidth
							mt="sm"
						>
							{t("home.resetFilters")}
						</Button>
					</Stack>
				</Box>
				{/* end scrollable content */}
			</Box>
			{/* end swipe container */}
		</Drawer>
	);

	// Shimmer skeleton
	const ShimmerSkeleton = (
		<RootPage blur tabBarChildren={SearchHeaderContent} noPadding>
			{FilterDrawer}
			<Container className="listings-container" px="md" pt="sm">
				<div
					className={
						viewMode === "masonry"
							? "listings-masonry-grid"
							: "listings-uniform-grid"
					}
				>
					{[...Array(6)].map((_, index) => (
						<Box
							key={index}
							mb={12}
							style={{
								borderRadius: radii.lg,
								overflow: "hidden",
								backgroundColor: "white",
								boxShadow: shadows.md,
							}}
						>
							<Skeleton height={180} radius={0} animate />
							<Box p={10}>
								<Skeleton height={14} width="70%" radius={6} mb={8} animate />
								<Skeleton height={10} width="50%" radius={6} animate />
							</Box>
						</Box>
					))}
				</div>
			</Container>
		</RootPage>
	);

	// Show skeletons while initial loading
	if (isLoading && listings.length === 0) {
		return ShimmerSkeleton;
	}

	// Empty state
	if (!isLoading && listings.length === 0) {
		return (
			<RootPage blur tabBarChildren={SearchHeaderContent} noPadding>
				{FilterDrawer}
				<Container className="listings-container">
					<Center py={60}>
						<Stack align="center" gap="md">
							<Box
								style={{
									width: 80,
									height: 80,
									borderRadius: radii.full,
									backgroundColor: "#e7f5ff",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
								}}
							>
								<IconSparkles size={36} color="#74c0fc" stroke={1.5} />
							</Box>
							<Text fw={600} size="md">
								{t("home.emptyTitle")}
							</Text>
							<Text c="dimmed" size="sm" ta="center" maw={240}>
								{t("home.emptyDescription")}
							</Text>
							{(searchQuery || activeFilterCount > 0) && (
								<Button
									variant="light"
									size="sm"
									radius={10}
									onClick={handleClearFilters}
								>
									{t("home.resetFilters")}
								</Button>
							)}
						</Stack>
					</Center>
				</Container>
			</RootPage>
		);
	}

	return (
		<RootPage blur tabBarChildren={SearchHeaderContent} noPadding>
			{FilterDrawer}
			<Container className="listings-container" px="md" pt="sm">
				{viewMode === "masonry" ? (
					<div className="listings-masonry-grid">
						{[0, 1].map((col) => (
							<div key={col} className="listings-masonry-col">
								{listings
									.filter((_, i) => i % 2 === col)
									.map((item) => (
										<ListingCard
											key={item.id}
											listing={item}
											layout="masonry"
											onClick={handleCardClick}
											isFavorited={favoritedIds.has(item.id)}
											onFavorite={(id) => toggleFavorite(id)}
										/>
									))}
							</div>
						))}
					</div>
				) : (
					<div className="listings-uniform-grid">
						{listings.map((item) => (
							<ListingCard
								key={item.id}
								listing={item}
								layout="grid"
								onClick={handleCardClick}
								isFavorited={favoritedIds.has(item.id)}
								onFavorite={(id) => toggleFavorite(id)}
							/>
						))}
					</div>
				)}

				{/* Load more trigger */}
				<div ref={loadMoreRef} style={{ height: 1 }} />

				{/* Loading indicator */}
				{isLoading && (
					<Center py="xl">
						<Stack align="center" gap={6}>
							<Loader size="sm" color="blue.5" />
							<Text size="xs" fw={600} c="dimmed">
								{t("common.loading")}
							</Text>
						</Stack>
					</Center>
				)}
			</Container>
		</RootPage>
	);
}

export const Home = {
	route: "/",
	Page,
};
