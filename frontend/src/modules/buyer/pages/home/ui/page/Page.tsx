import { CSSProperties, useEffect, useCallback, useRef, useState } from "react";
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
	Chip,
	RangeSlider,
	NumberInput,
	Switch,
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
	IconCash,
	IconDoor,
	IconMapPin,
	IconBuildingEstate,
	IconRulerMeasure,
	IconTools,
	IconBuilding,
	IconStairs,
	IconPhoto,
	IconReceipt2,
	IconKey,
	IconClock,
	IconHeart,
	IconHeartFilled,
} from "@tabler/icons-react";
import {
	getConditionFilterOpts,
	getBuildingTypeFilterOpts,
} from "@shared/constants/listingFilterOptions";
import { DealTypeGrid, PropertyTypeGrid } from "@shared/ui/FilterCards";
import { shadows, radii, surface } from "@app/styles/theme";
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
import { fetchUnifiedFeed } from "@shared/api/crawlerListings";
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
	$isSubscriptionsLoading,
	$isRecommendedLoading,
	$hasMore,
	$favoritedIds,
	$searchQuery,
	$filters,
	$activeTab,
	pageOpened,
	loadMore,
	toggleFavorite,
	searchQueryChanged,
	filtersChanged,
	filtersReplaced,
	applyFilters,
	clearFilters,
	// tabChanged, — нужен только таб-бару, скрытому до запуска (см. BACKLOG.md)
	buildFeedParams,
	type HomeFilters,
	type HomeSort,
	// type HomeTab, — нужен только таб-бару, скрытому до запуска (см. BACKLOG.md)
} from "../../model";
import {
	$savedSearches,
	createSavedSearchFx,
	deleteSavedSearchFx,
	fetchSavedSearchesFx,
} from "@modules/buyer/feature/saved-searches";
import { notifications } from "@mantine/notifications";
import { useAuth } from "@app/providers/useAuth";
import { HomeBanners } from "@modules/buyer/feature/home-banners";
import { useTelegramBackClose } from "@shared/hooks/useTelegramBackClose";

// Shared pill/toggle style for single- and multi-select filter chips.
const toggleChipStyle = (active: boolean): CSSProperties => ({
	height: 36,
	padding: "0 16px",
	fontSize: 13,
	fontWeight: 600,
	borderRadius: 18,
	backgroundColor: active ? "#228be6" : "#f1f3f5",
	color: active ? "#fff" : "#495057",
	display: "inline-flex",
	alignItems: "center",
	cursor: "pointer",
	transition: "all 0.15s ease",
});

function Page() {
	const { t } = useTranslation(["buyer", "seller"]);
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const [
		listings,
		isLoading,
		isSubscriptionsLoading,
		isRecommendedLoading,
		hasMore,
		favoritedIds,
		searchQuery,
		filters,
		userStats,
		activeTab,
	] = useUnit([
		$listings,
		$isLoading,
		$isSubscriptionsLoading,
		$isRecommendedLoading,
		$hasMore,
		$favoritedIds,
		$searchQuery,
		$filters,
		$userStats,
		$activeTab,
	]);
	// Tab-aware loading flag so spinners and skeletons reflect the active feed.
	const tabIsLoading =
		activeTab === "subscriptions"
			? isSubscriptionsLoading
			: activeTab === "recommended"
				? isRecommendedLoading
				: isLoading;
	const observerRef = useRef<IntersectionObserver | null>(null);
	const loadMoreRef = useRef<HTMLDivElement | null>(null);
	const initializedRef = useRef(false);
	const [drawerOpened, { open: openDrawer, close: closeDrawer }] =
		useDisclosure(false);
	useTelegramBackClose(drawerOpened, closeDrawer);
	const { openSearch, searchOpen } = useLayoutContext();
	const { isAuthenticated } = useAuth();

	// Declare sort/filter local state BEFORE saved-search logic so sortBy is in scope
	const [sortBy, setSortBy] = useState<HomeSort>("recommended");
	const [viewMode] = useState<"grid" | "masonry">("grid");
	const [localPriceRange, setLocalPriceRange] = useState<[number, number]>([
		0, 500000,
	]);
	const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
	const [draftFilters, setDraftFilters] = useState<HomeFilters>(filters);
	// Live result count for the draft filters, shown on the Apply button.
	const [draftResultsCount, setDraftResultsCount] = useState<number | null>(
		null,
	);

	// ── Saved Searches ──────────────────────────────────────────────────────
	const savedSearches = useUnit($savedSearches);

	const currentSavedSearch = savedSearches.find((s) => {
		const sameQuery = (s.query || "") === (searchQuery || "");
		
		// To avoid strictly ordering differences, we compare fields explicitly
		const sameFilters = 
			s.filters.deal_type === filters.type?.[0] &&
			s.filters.property_type === filters.property_type?.[0] &&
			s.filters.price_min === (filters.price_min ?? null) &&
			s.filters.price_max === (filters.price_max ?? null) &&
			s.filters.district === filters.district?.[0] &&
			s.filters.region === filters.region?.[0] &&
			JSON.stringify(s.filters.rooms || []) === JSON.stringify(filters.rooms || []);
			
		return sameQuery && sameFilters;
	});

	const isSaved = !!currentSavedSearch;

	// Fetch saved searches once authenticated
	const savedSearchesFetchedRef = useRef(false);
	useEffect(() => {
		if (!isAuthenticated || savedSearchesFetchedRef.current) return;
		savedSearchesFetchedRef.current = true;
		fetchSavedSearchesFx();
	}, [isAuthenticated]);

	const handleToggleSaveSearch = useCallback(() => {
		if (!isAuthenticated) {
			navigate("/auth");
			return;
		}

		if (currentSavedSearch) {
			// Show toast immediately (optimistic)
			notifications.show({
				message: t("favorites.searches.deleted", { ns: "buyer" }),
				color: "gray",
				autoClose: 2000,
			});
			// Fire effect (store updates via .on(doneData))
			deleteSavedSearchFx(currentSavedSearch.id).catch(() => {
				notifications.show({
					message: t("favorites.searches.deleteError", { ns: "buyer" }),
					color: "red",
					autoClose: 3000,
				});
			});
		} else {
			// Show toast immediately (optimistic)
			notifications.show({
				message: t("favorites.searches.saved", { ns: "buyer" }),
				color: "blue",
				autoClose: 2000,
			});
			// Fire effect (store updates via .on(doneData))
			createSavedSearchFx({
				query: searchQuery || null,
				filters: {
					deal_type: filters.type?.[0] as "sell" | "rent" | undefined,
					property_type: filters.property_type?.[0] as "apartment" | "house" | "commercial" | "land" | undefined,
					rooms: filters.rooms,
					price_min: filters.price_min ?? null,
					price_max: filters.price_max ?? null,
					district: filters.district?.[0],
					region: filters.region?.[0],
				},
				sort: sortBy,
			}).catch(() => {
				notifications.show({
					message: t("favorites.searches.saveError", { ns: "buyer" }),
					color: "red",
					autoClose: 3000,
				});
			});
		}
	}, [isAuthenticated, currentSavedSearch, searchQuery, filters, sortBy, navigate, t]);


	// Show heart only when there's an active query or any filter
	const hasActiveSearch = !!searchQuery || Object.keys(filters).some(
		(k) => (filters as Record<string, unknown>)[k] !== undefined && (filters as Record<string, unknown>)[k] !== null
	);

	const filterScrollRef = useRef<HTMLDivElement>(null);
	const filterSwipe = useSwipeDismiss({
		onClose: closeDrawer,
		threshold: 120,
		resistance: 0.6,
		scrollRef: filterScrollRef,
		enabled: drawerOpened,
	});

	// Sync drawer values when it opens
	useEffect(() => {
		if (drawerOpened) {
			setDraftFilters(filters);
			setSortBy(filters.sort ?? "recommended");
			const min = filters.price_min || 0;
			const isRentOnly = filters.type?.length === 1 && filters.type[0] === "rent";
			const max = filters.price_max || (isRentOnly ? 5000 : 500000);
			setLocalPriceRange([min, max]);
			setSelectedRegion(filters.region?.[0] || null);
		}
	}, [drawerOpened, filters]);

	// Live count of listings matching the draft (debounced). Drives the
	// "Показать N" label so the user sees the result size BEFORE applying —
	// and notices immediately when a combination yields zero results.
	useEffect(() => {
		if (!drawerOpened) return;
		let cancelled = false;
		const timer = setTimeout(() => {
			fetchUnifiedFeed({ ...buildFeedParams(1, draftFilters), per_page: 1 })
				.then((res) => {
					if (!cancelled) setDraftResultsCount(res.total);
				})
				.catch(() => {
					// Count is a progressive enhancement — fall back to plain "Apply".
					if (!cancelled) setDraftResultsCount(null);
				});
		}, 350);
		return () => {
			cancelled = true;
			clearTimeout(timer);
		};
	}, [drawerOpened, draftFilters]);

	// Initialize from URL params
	useEffect(() => {
		if (initializedRef.current) return;
		initializedRef.current = true;

		const urlFilters: Partial<HomeFilters> = {};
		const q = searchParams.get("q");
		const type = searchParams.get("type");
		const propertyType = searchParams.get("property_type");
		const rooms = searchParams.get("rooms");
		const priceMin = searchParams.get("price_min");
		const priceMax = searchParams.get("price_max");
		const region = searchParams.get("region");
		const district = searchParams.get("district");

		if (q) urlFilters.q = q;
		if (type) urlFilters.type = type.split(",") as any;
		if (propertyType) urlFilters.property_type = propertyType.split(",") as any;
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
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [searchParams]);

	// One badge unit per filter GROUP (a range is one filter, not two). Floor
	// range, the not-first/not-last toggles and the storeys range share one
	// card, so they count as a single group.
	const activeFilterCount = [
		filters.type?.length,
		filters.property_type?.length,
		filters.rooms?.length,
		filters.price_min || filters.price_max,
		filters.region?.length,
		filters.district?.length,
		filters.area_min || filters.area_max,
		filters.floor_min ||
			filters.floor_max ||
			filters.total_floors_min ||
			filters.total_floors_max ||
			filters.not_first_floor ||
			filters.not_last_floor,
		filters.building_type,
		filters.condition?.length,
		filters.has_photo,
		filters.posted_within,
		filters.mortgage_ok || filters.installment_ok || filters.halol_ok,
		filters.furnished ||
			filters.allowed_pets ||
			filters.allowed_students ||
			filters.utilities_incl,
		// Rent period is its own card now → its own badge unit.
		filters.rent_period,
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

	const handleApplyDraft = () => {
		// Replace (not merge) so a reset draft actually clears applied filters.
		filtersReplaced({
			...draftFilters,
			sort: sortBy === "recommended" ? undefined : sortBy,
		});
		applyFiltersAndClearScroll();
		closeDrawer();
	};

	// Reset ONLY the draft: the drawer stays open and the applied filters /
	// feed are untouched until the user presses Apply. The search query is
	// not a drawer control, so it survives the reset.
	const handleResetDraft = () => {
		setDraftFilters(draftFilters.q ? { q: draftFilters.q } : {});
		setSortBy("recommended");
		setLocalPriceRange([0, 500000]);
		setSelectedRegion(null);
	};

	const handleTypeChange = (value: string) => {
		let newTypes = draftFilters.type ? [...draftFilters.type] : [];
		if (newTypes.includes(value as any)) {
			newTypes = newTypes.filter((v) => v !== value);
		} else {
			newTypes.push(value as any);
		}

		const isRentOnlyNext = newTypes.length === 1 && newTypes[0] === "rent";
		const newMax = isRentOnlyNext ? 5000 : 500000;
		setLocalPriceRange([0, newMax]);
		setDraftFilters((prev) => ({
			...prev,
			type: newTypes.length > 0 ? newTypes : undefined,
			price_min: undefined,
			price_max: undefined,
		}));
	};

	const handleQuickFilter = (propertyType: string) => {
		let newProps = draftFilters.property_type ? [...draftFilters.property_type] : [];
		if (newProps.includes(propertyType as any)) {
			newProps = newProps.filter((p) => p !== propertyType);
		} else {
			newProps.push(propertyType as any);
		}
		setDraftFilters((prev) => ({
			...prev,
			property_type: newProps.length > 0 ? newProps : undefined,
		}));
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
						<Box style={{ position: "relative" }}>
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
							{activeFilterCount > 0 && (
								<Box
									style={{
										position: "absolute",
										top: -2,
										right: -2,
										minWidth: 16,
										height: 16,
										borderRadius: 8,
										backgroundColor: "#228be6",
										border: "2px solid #ffffff",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										padding: "0 4px",
										pointerEvents: "none",
									}}
								>
									<Text size="9px" fw={800} c="white" style={{ lineHeight: 1 }}>
										{activeFilterCount}
									</Text>
								</Box>
							)}
						</Box>
					</UnstyledButton>

					{/* ── Save Search heart ── shown when query or filters are active */}
					{hasActiveSearch && (
						<ActionIcon
							variant="subtle"
							color={isSaved ? "red" : "gray"}
							size={42}
							radius="xl"
							onClick={handleToggleSaveSearch}
							style={{ transition: "transform 0.15s ease" }}
						>
							{isSaved ? (
								<IconHeartFilled size={22} style={{ color: "#ff6b6b" }} />
							) : (
								<IconHeart size={22} stroke={1.6} />
							)}
						</ActionIcon>
					)}

					{/* ── Notifications bell ── */}
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
		</>
	);

	// Filter drawer
	const filterTransition = filterSwipe.isDragging
		? "none"
		: filterSwipe.isClosing
			? "transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
			: "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";

	// Price slider bounds depend on the drafted deal type: rent-only budgets
	// live on a much smaller scale than purchase prices.
	const isRentOnly =
		draftFilters.type?.length === 1 && draftFilters.type[0] === "rent";
	const sliderMax = isRentOnly ? 5000 : 500000;
	const sliderStep = isRentOnly ? 100 : 5000;

	// Deal-terms cards are contextual and appear only after the user picks
	// the matching deal type: sale terms when «Продажа» is selected, rent
	// terms when «Аренда». Nothing selected → neither card.
	const isSaleContext = !!draftFilters.type?.includes("sell");
	const isRentContext = !!draftFilters.type?.includes("rent");

	const renderChipGroup = (
		options: { value: string; label: string }[],
		value: string[] = [],
		onChange: (v: string[]) => void
	) => {
		const toggle = (optValue: string) => {
			if (value.includes(optValue)) {
				onChange(value.filter((v) => v !== optValue));
			} else {
				onChange([...value, optValue]);
			}
		};

		return (
			<Group gap={8} wrap="wrap">
				{options.map((opt) => (
					<UnstyledButton
						key={opt.value}
						onClick={() => toggle(opt.value)}
						style={toggleChipStyle(value.includes(opt.value))}
					>
						{opt.label}
					</UnstyledButton>
				))}
			</Group>
		);
	};

	// Paired "от / до" number inputs (+ optional range slider, same pattern
	// as the price card) reused by the area, floor and storeys controls.
	// Empty input clears the bound (undefined). Slider semantics mirror the
	// price card: left thumb at the scale start / right thumb at the scale
	// end = no bound; typed values beyond the scale are kept verbatim and
	// the slider just clamps its display.
	const renderNumberRange = (opts: {
		minValue?: number;
		maxValue?: number;
		onMin: (v?: number) => void;
		onMax: (v?: number) => void;
		suffix?: string;
		min?: number;
		slider?: {
			max: number;
			step: number;
			color?: string;
			marks?: { value: number; label: string }[];
		};
	}) => {
		const toNum = (v: number | string) =>
			typeof v === "number" ? v : undefined;
		const scaleMin = opts.min ?? 0;
		return (
			<Box>
				<Group grow gap={10}>
					<NumberInput
						label={t("filter.from")}
						size="sm"
						radius={10}
						min={scaleMin}
						allowNegative={false}
						allowDecimal={false}
						thousandSeparator=" "
						inputMode="numeric"
						hideControls
						suffix={opts.suffix}
						value={opts.minValue ?? ""}
						onChange={(v) => opts.onMin(toNum(v))}
					/>
					<NumberInput
						label={t("filter.to")}
						size="sm"
						radius={10}
						min={scaleMin}
						allowNegative={false}
						allowDecimal={false}
						thousandSeparator=" "
						inputMode="numeric"
						hideControls
						suffix={opts.suffix}
						value={opts.maxValue ?? ""}
						onChange={(v) => opts.onMax(toNum(v))}
					/>
				</Group>
				{opts.slider && (
					<Box px={8} mt={10}>
						<RangeSlider
							color={opts.slider.color ?? "violet"}
							min={scaleMin}
							max={opts.slider.max}
							step={opts.slider.step}
							value={[
								Math.min(opts.minValue ?? scaleMin, opts.slider.max),
								Math.min(opts.maxValue ?? opts.slider.max, opts.slider.max),
							]}
							onChange={(value) => {
								opts.onMin(value[0] > scaleMin ? value[0] : undefined);
								opts.onMax(
									value[1] < (opts.slider as { max: number }).max
										? value[1]
										: undefined,
								);
							}}
							marks={opts.slider.marks}
							labelAlwaysOn={false}
							mb={opts.slider.marks ? 24 : 8}
						/>
					</Box>
				)}
			</Box>
		);
	};

	// Deal-terms toggle chips. Each setter names its field explicitly (no
	// computed keys) so the patch stays assignable to HomeFilters.
	const saleTermChips = [
		{
			active: !!draftFilters.mortgage_ok,
			label: t("seller:createListing.mortgageOk"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					mortgage_ok: p.mortgage_ok ? undefined : true,
				})),
		},
		{
			active: !!draftFilters.installment_ok,
			label: t("seller:createListing.installmentOk"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					installment_ok: p.installment_ok ? undefined : true,
				})),
		},
		{
			active: !!draftFilters.halol_ok,
			label: t("seller:createListing.halolOk"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					halol_ok: p.halol_ok ? undefined : true,
				})),
		},
	];

	const rentTermChips = [
		{
			active: !!draftFilters.furnished,
			label: t("filter.furnished"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					furnished: p.furnished ? undefined : true,
				})),
		},
		{
			active: !!draftFilters.allowed_pets,
			label: t("seller:createListing.allowedPetsLabel"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					allowed_pets: p.allowed_pets ? undefined : true,
				})),
		},
		{
			active: !!draftFilters.allowed_students,
			label: t("seller:createListing.allowedStudentsLabel"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					allowed_students: p.allowed_students ? undefined : true,
				})),
		},
		{
			active: !!draftFilters.utilities_incl,
			label: t("seller:createListing.utilitiesInclLabel"),
			toggle: () =>
				setDraftFilters((p) => ({
					...p,
					utilities_incl: p.utilities_incl ? undefined : true,
				})),
		},
	];

	const rentPeriodChips = [
		{ value: "long_term" as const, label: t("seller:createListing.rentPeriodLongTerm") },
		{ value: "daily" as const, label: t("seller:createListing.rentPeriodDaily") },
	];

	const FilterDrawer = (
		<Drawer
			opened={drawerOpened}
			onClose={closeDrawer}
			withCloseButton={false}
			position="bottom"
			size="auto"
			zIndex={10001}
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
					{/* pb must clear the floating footer: 56px buttons + 16px paddings
					    + iOS safe-area inset (up to ~34px), otherwise the last card's
					    controls hide behind the buttons. */}
					<Stack gap="md" pb={140} px="md">
						{/* Sorting */}
						<PreferenceCard
							icon={IconArrowsSort}
							iconColor="#FF6E01"
							iconBg="#FFF4E6"
							title={t("search.sortBy")}
							isActive={sortBy !== "recommended"}
						>
							<Chip.Group
								multiple={false}
								value={sortBy}
								onChange={(value) => setSortBy(value as HomeSort)}
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

						{/* Deal type — placed ABOVE price: the price scale depends on it
						    (rent budgets vs purchase prices), so the user picks the deal
						    first and never has an entered price silently reset. */}
						<PreferenceCard
							icon={IconTags}
							iconColor="#228be6"
							iconBg="#e7f5ff"
							title={t("preferences.listingType")}
							description={t("preferences.desc.listingType")}
							isActive={(draftFilters.type?.length ?? 0) > 0}
						>
							<DealTypeGrid
								value={draftFilters.type || []}
								onChange={handleTypeChange}
							/>
						</PreferenceCard>

						{/* Rent period — its own block right under the deal type: appears
						    the moment «Аренда» is picked, hidden for sales. */}
						{isRentContext && (
						<PreferenceCard
							icon={IconClock}
							iconColor="#0ca678"
							iconBg="#e6fcf5"
							title={t("seller:createListing.rentPeriodLabel")}
							isActive={!!draftFilters.rent_period}
						>
							<Group gap={8} wrap="wrap">
								{rentPeriodChips.map((c) => {
									const active = draftFilters.rent_period === c.value;
									return (
										<UnstyledButton
											key={c.value}
											onClick={() =>
												setDraftFilters((prev) => ({
													...prev,
													rent_period: active ? undefined : c.value,
												}))
											}
											style={toggleChipStyle(active)}
										>
											{c.label}
										</UnstyledButton>
									);
								})}
							</Group>
						</PreferenceCard>
						)}
						{/* Property type */}
						<PreferenceCard
							icon={IconBuildingEstate}
							iconColor="#40c057"
							iconBg="#ebfbee"
							title={t("preferences.propertyType")}
							description={t("preferences.desc.propertyType")}
							isActive={(draftFilters.property_type?.length ?? 0) > 0}
						>
							<PropertyTypeGrid
								value={draftFilters.property_type || []}
								onChange={handleQuickFilter}
							/>
						</PreferenceCard>

						{/* Building type (new / secondary) */}
						<PreferenceCard
							icon={IconBuilding}
							iconColor="#FF6E01"
							iconBg="#FFF4E6"
							title={t("seller:createListing.buildingType")}
							isActive={!!draftFilters.building_type}
						>
							<Group gap={8} wrap="wrap">
								{getBuildingTypeFilterOpts(t).map((opt) => {
									const active = draftFilters.building_type === opt.value;
									return (
										<UnstyledButton
											key={opt.value}
											onClick={() =>
												setDraftFilters((prev) => ({
													...prev,
													building_type: active ? undefined : opt.value,
												}))
											}
											style={toggleChipStyle(active)}
										>
											{opt.label}
										</UnstyledButton>
									);
								})}
							</Group>
						</PreferenceCard>

						{/* Price range — text inputs for precision (a finger on a
						    $0–500k slider moves in ~$1.5k/px jumps), slider for feel. */}
						<PreferenceCard
							icon={IconCash}
							iconColor="#be4bdb"
							iconBg="#f3f0ff"
							title={t("preferences.priceRange")}
							description={t("preferences.desc.priceRange")}
							isActive={!!draftFilters.price_min || !!draftFilters.price_max}
						>
							<Group grow mb={12} gap={10}>
								<NumberInput
									label={t("filter.from")}
									size="sm"
									radius={10}
									min={0}
									allowNegative={false}
									allowDecimal={false}
									thousandSeparator=" "
									inputMode="numeric"
									hideControls
									prefix="$ "
									placeholder="$ 0"
									value={localPriceRange[0] > 0 ? localPriceRange[0] : ""}
									onChange={(v) => {
										const min = typeof v === "number" ? Math.max(0, v) : 0;
										setLocalPriceRange(([, hi]) => [min, hi]);
										setDraftFilters((prev) => ({
											...prev,
											price_min: min > 0 ? min : undefined,
										}));
									}}
								/>
								<NumberInput
									label={t("filter.to")}
									size="sm"
									radius={10}
									min={0}
									allowNegative={false}
									allowDecimal={false}
									thousandSeparator=" "
									inputMode="numeric"
									hideControls
									prefix="$ "
									placeholder={`$ ${sliderMax.toLocaleString("ru-RU")}`}
									value={
										localPriceRange[1] < sliderMax ? localPriceRange[1] : ""
									}
									onChange={(v) => {
										// Empty / cleared input = no upper bound. Typed values
										// above the slider scale are kept verbatim — that is
										// the whole point of having a text field.
										const max =
											typeof v === "number" && v > 0 ? v : sliderMax;
										setLocalPriceRange(([lo]) => [lo, max]);
										setDraftFilters((prev) => ({
											...prev,
											price_max: max === sliderMax ? undefined : max,
										}));
									}}
								/>
							</Group>
							<Box px={8}>
								<RangeSlider
									color="violet"
									min={0}
									max={sliderMax}
									step={sliderStep}
									value={[
										Math.min(localPriceRange[0], sliderMax),
										Math.min(localPriceRange[1], sliderMax),
									]}
									onChange={(value) =>
										setLocalPriceRange(value as [number, number])
									}
									onChangeEnd={(value) => {
										setDraftFilters((prev) => ({
											...prev,
											price_min: value[0] > 0 ? value[0] : undefined,
											price_max:
												value[1] < sliderMax ? value[1] : undefined,
										}));
									}}
									marks={
										isRentOnly
											? [
													{ value: 0, label: "$0" },
													{ value: 2500, label: "$2.5k" },
													{ value: 5000, label: "$5k+" },
												]
											: [
													{ value: 0, label: "$0" },
													{ value: 250000, label: "$250k" },
													{ value: 500000, label: "$500k+" },
												]
									}
									labelAlwaysOn={false}
									mb={24}
								/>
							</Box>
						</PreferenceCard>

						{/* Rooms */}
						<PreferenceCard
							icon={IconDoor}
							iconColor="#ff922b"
							iconBg="#fff4e6"
							title={t("preferences.rooms")}
							description={t("preferences.desc.rooms")}
							isActive={(draftFilters.rooms?.length ?? 0) > 0}
						>
							<Chip.Group
								multiple
								value={draftFilters.rooms?.map(String) || []}
								onChange={(values) => {
									setDraftFilters((prev) => ({
										...prev,
										rooms:
											values.length > 0
												? values.map((v) => (v === "0" ? 0 : parseInt(v)))
												: undefined,
									}));
								}}
							>
								<Group gap={8}>
									{ROOMS_OPTIONS_KEYS.map((room) => {
										const val = room === "studio" ? "0" : room;
										const isActive = (
											draftFilters.rooms?.map(String) || []
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

						{/* Region & District */}
						<PreferenceCard
							icon={IconMapPin}
							iconColor="#e64980"
							iconBg="#fff0f6"
							title={t("preferences.region")}
							description={t("preferences.desc.region")}
							isActive={!!draftFilters.region || !!draftFilters.district}
						>
							<Box>
								<Text size="sm" fw={500} mb={6}>{t("home.allRegions")}</Text>
								<Group gap={8} wrap="wrap" pb={4}>
									{getRegionKeys().map((key) => {
										const isActive = selectedRegion === key;
										return (
											<UnstyledButton
												key={key}
												onClick={() => {
													const newRegion = isActive ? null : key;
													setSelectedRegion(newRegion);
													setDraftFilters((prev) => ({
														...prev,
														region: newRegion ? [newRegion] : undefined,
														district: undefined,
													}));
												}}
												style={{
													height: 36,
													padding: "0 16px",
													fontSize: 13,
													fontWeight: 600,
													borderRadius: 18,
													backgroundColor: isActive ? "#228be6" : "#f1f3f5",
													color: isActive ? "#fff" : "#495057",
													display: "inline-flex",
													alignItems: "center",
													cursor: "pointer",
													transition: "all 0.15s ease",
												}}
											>
												{translateRegion(key, t)}
											</UnstyledButton>
										);
									})}
								</Group>
							</Box>

							{selectedRegion && (
								<Box mt="md">
									<Text size="sm" fw={500} mb={6}>{t("home.allDistricts")}</Text>
									<Group gap={8} pb={8} wrap="wrap">
										{getDistrictsForRegion(selectedRegion).map((key) => {
											const currentDistricts = draftFilters.district || [];
											const isActive = currentDistricts.includes(key);
											return (
												<UnstyledButton
													key={key}
													onClick={() => {
														const newDistricts = isActive
															? currentDistricts.filter(d => d !== key)
															: [...currentDistricts, key];
														setDraftFilters((prev) => ({
															...prev,
															district: newDistricts.length > 0 ? newDistricts : undefined,
														}));
													}}
													style={{
														height: 36,
														padding: "0 16px",
														fontSize: 13,
														fontWeight: 600,
														borderRadius: 18,
														backgroundColor: isActive ? "#228be6" : "#f1f3f5",
														color: isActive ? "#fff" : "#495057",
														display: "inline-flex",
														alignItems: "center",
														cursor: "pointer",
														transition: "all 0.15s ease",
													}}
												>
													{translateDistrict(key, t)}
												</UnstyledButton>
											);
										})}
									</Group>
								</Box>
							)}
						</PreferenceCard>

						{/* Area (m²) */}
						<PreferenceCard
							icon={IconRulerMeasure}
							iconColor="#40c057"
							iconBg="#ebfbee"
							title={t("seller:createListing.area")}
							isActive={!!draftFilters.area_min || !!draftFilters.area_max}
						>
							{renderNumberRange({
								minValue: draftFilters.area_min,
								maxValue: draftFilters.area_max,
								onMin: (v) => setDraftFilters((prev) => ({ ...prev, area_min: v })),
								onMax: (v) => setDraftFilters((prev) => ({ ...prev, area_max: v })),
								suffix: ` ${t("listing.area")}`,
								slider: {
									max: 500,
									step: 5,
									color: "green",
									marks: [
										{ value: 0, label: "0" },
										{ value: 250, label: "250" },
										{ value: 500, label: "500+" },
									],
								},
							})}
						</PreferenceCard>

						{/* Floor & storeys */}
						<PreferenceCard
							icon={IconStairs}
							iconColor="#be4bdb"
							iconBg="#f3f0ff"
							title={t("filter.floorSection")}
							isActive={
								!!draftFilters.floor_min ||
								!!draftFilters.floor_max ||
								!!draftFilters.total_floors_min ||
								!!draftFilters.total_floors_max ||
								!!draftFilters.not_first_floor ||
								!!draftFilters.not_last_floor
							}
						>
							<Stack gap={14}>
								<Box>
									<Text size="sm" fw={500} mb={6}>
										{t("seller:createListing.floor")}
									</Text>
									{renderNumberRange({
										minValue: draftFilters.floor_min,
										maxValue: draftFilters.floor_max,
										onMin: (v) => setDraftFilters((prev) => ({ ...prev, floor_min: v })),
										onMax: (v) => setDraftFilters((prev) => ({ ...prev, floor_max: v })),
										slider: {
											max: 30,
											step: 1,
											marks: [
												{ value: 0, label: "0" },
												{ value: 15, label: "15" },
												{ value: 30, label: "30+" },
											],
										},
									})}
								</Box>
								<Group gap={8} wrap="wrap">
									<UnstyledButton
										onClick={() =>
											setDraftFilters((prev) => ({
												...prev,
												not_first_floor: draftFilters.not_first_floor ? undefined : true,
											}))
										}
										style={toggleChipStyle(!!draftFilters.not_first_floor)}
									>
										{t("filter.notFirstFloor")}
									</UnstyledButton>
									<UnstyledButton
										onClick={() =>
											setDraftFilters((prev) => ({
												...prev,
												not_last_floor: draftFilters.not_last_floor ? undefined : true,
											}))
										}
										style={toggleChipStyle(!!draftFilters.not_last_floor)}
									>
										{t("filter.notLastFloor")}
									</UnstyledButton>
								</Group>
								<Box>
									<Text size="sm" fw={500} mb={6}>
										{t("seller:createListing.totalFloors")}
									</Text>
									{renderNumberRange({
										minValue: draftFilters.total_floors_min,
										maxValue: draftFilters.total_floors_max,
										onMin: (v) =>
											setDraftFilters((prev) => ({ ...prev, total_floors_min: v })),
										onMax: (v) =>
											setDraftFilters((prev) => ({ ...prev, total_floors_max: v })),
										min: 1,
										slider: {
											max: 30,
											step: 1,
											marks: [
												{ value: 1, label: "1" },
												{ value: 15, label: "15" },
												{ value: 30, label: "30+" },
											],
										},
									})}
								</Box>
							</Stack>
						</PreferenceCard>

						{/* Condition / repair */}
						<PreferenceCard
							icon={IconTools}
							iconColor="#228be6"
							iconBg="#e7f5ff"
							title={t("seller:createListing.condition")}
							isActive={(draftFilters.condition?.length ?? 0) > 0}
						>
							{renderChipGroup(
								getConditionFilterOpts(t),
								draftFilters.condition || [],
								(v) =>
									setDraftFilters((prev) => ({
										...prev,
										condition: v.length > 0 ? v : undefined,
									})),
							)}
						</PreferenceCard>

						{/* Photo & freshness */}
						<PreferenceCard
							icon={IconPhoto}
							iconColor="#15aabf"
							iconBg="#e3fafc"
							title={t("filter.extraSection")}
							isActive={!!draftFilters.has_photo || !!draftFilters.posted_within}
						>
							<Switch
								checked={!!draftFilters.has_photo}
								onChange={(e) => {
									// Read `checked` synchronously: React nulls the synthetic
									// event's currentTarget once the handler returns, and the
									// setState updater below runs deferred — reading
									// e.currentTarget inside it would crash with null.
									const checked = e.currentTarget.checked;
									setDraftFilters((prev) => ({
										...prev,
										has_photo: checked || undefined,
									}));
								}}
								label={t("filter.onlyWithPhoto")}
								color="cyan"
								mb={14}
							/>
							<Text size="sm" fw={500} mb={6}>
								{t("filter.postedLabel")}
							</Text>
							<Group gap={8} wrap="wrap">
								{([
									[1, t("filter.posted1d")],
									[7, t("filter.posted7d")],
									[30, t("filter.posted30d")],
								] as const).map(([days, label]) => {
									const active = draftFilters.posted_within === days;
									return (
										<UnstyledButton
											key={days}
											onClick={() =>
												setDraftFilters((prev) => ({
													...prev,
													posted_within: active ? undefined : days,
												}))
											}
											style={toggleChipStyle(active)}
										>
											{label}
										</UnstyledButton>
									);
								})}
							</Group>
						</PreferenceCard>

						{/* Sale terms — mortgage / installment / halal (platform-only) */}
						{isSaleContext && (
						<PreferenceCard
							icon={IconReceipt2}
							iconColor="#fa5252"
							iconBg="#fff5f5"
							title={t("filter.saleTerms")}
							isActive={
								!!draftFilters.mortgage_ok ||
								!!draftFilters.installment_ok ||
								!!draftFilters.halol_ok
							}
						>
							<Group gap={8} wrap="wrap">
								{saleTermChips.map((c) => (
									<UnstyledButton
										key={c.label}
										onClick={c.toggle}
										style={toggleChipStyle(c.active)}
									>
										{c.label}
									</UnstyledButton>
								))}
							</Group>
						</PreferenceCard>
						)}

						{/* Rent terms — furniture / pets / students / utilities (platform-only).
						    The rent PERIOD lives in its own card right under the deal type. */}
						{isRentContext && (
						<PreferenceCard
							icon={IconKey}
							iconColor="#0ca678"
							iconBg="#e6fcf5"
							title={t("filter.rentTerms")}
							isActive={
								!!draftFilters.furnished ||
								!!draftFilters.allowed_pets ||
								!!draftFilters.allowed_students ||
								!!draftFilters.utilities_incl
							}
						>
							<Group gap={8} wrap="wrap">
								{rentTermChips.map((c) => (
									<UnstyledButton
										key={c.label}
										onClick={c.toggle}
										style={toggleChipStyle(c.active)}
									>
										{c.label}
									</UnstyledButton>
								))}
							</Group>
						</PreferenceCard>
						)}
					</Stack>
				</Box>
				
				{/* Fixed Floating Footer */}
				<Box
					style={{
						position: "absolute",
						bottom: 0,
						left: 0,
						right: 0,
						paddingBottom: "var(--safe-area-inset-bottom)",
						zIndex: 10,
						pointerEvents: "none",
					}}
				>
					<Box
						style={{
							padding: "4px 12px 12px",
							maxWidth: 500,
							margin: "0 auto",
						}}
					>
						<Box
							style={{
								display: "flex",
								alignItems: "center",
								height: 56,
								pointerEvents: "auto",
								gap: "10px",
							}}
						>
							<Button
								style={{ flex: 1 }}
								h="100%"
								radius={100}
								c="#495057"
								fw={600}
								fz={14}
								onClick={handleResetDraft}
								styles={{
									root: {
										// Solid surfaces: translucent buttons over scrolling
										// content made both labels hard to read (WCAG fail).
										backgroundColor: "#ffffff",
										border: "1px solid #dee2e6",
										boxShadow: "0 4px 15px rgba(0,0,0,0.08)",
									},
								}}
							>
								{t("common.reset")}
							</Button>
							<Button
								style={{ flex: 1 }}
								h="100%"
								radius={100}
								c="white"
								fw={600}
								fz={14}
								onClick={handleApplyDraft}
								styles={{
									root: {
										backgroundColor: "#40A7E3",
										boxShadow: "0 4px 15px rgba(64, 167, 227, 0.4)",
									},
								}}
							>
								{draftResultsCount !== null
									? t("home.showResults", {
											value: draftResultsCount.toLocaleString("ru-RU"),
										})
									: t("action.apply")}
							</Button>
						</Box>
					</Box>
				</Box>
			</Box>
		</Drawer>
	);

	// Shimmer skeleton
	const ShimmerSkeleton = (
		<RootPage title="UCHAR" tabBarChildren={SearchHeaderContent} noPadding>
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

	// F048 — Three-tab bar (Feed / Subscriptions / Recommended).
	// СКРЫТ до запуска (2026-06-12): вернём после запуска как 2 таба
	// («Для вас» / «Подписки») — детали в BACKLOG.md, «Вернуть табы на главную».
	// Для возврата раскомментировать блок ниже и импорты tabChanged / type HomeTab.
	// Пока табов нет, лента работает в режиме по умолчанию ($activeTab = "feed").
	const HomeTabBar = null;
	/*
	const HomeTabBar = (
		<Box
			px="md"
			pt={6}
			pb={4}
			style={{ maxWidth: 980, margin: "0 auto" }}
		>
			<Group gap={6} wrap="nowrap">
				{(["feed", "subscriptions", "recommended"] as HomeTab[]).map(
					(tab) => {
						const isActive = activeTab === tab;
						return (
							<UnstyledButton
								key={tab}
								onClick={() => {
									if (activeTab !== tab) tabChanged(tab);
								}}
								style={{
									flex: 1,
									height: 36,
									borderRadius: 18,
									backgroundColor: isActive ? "#228be6" : "#f1f3f5",
									color: isActive ? "#fff" : "#495057",
									display: "inline-flex",
									alignItems: "center",
									justifyContent: "center",
									fontWeight: 600,
									fontSize: 13,
									transition: "all 0.15s ease",
								}}
							>
								{t(`home.tabs.${tab}`)}
							</UnstyledButton>
						);
					},
				)}
			</Group>
		</Box>
	);
	*/

	// Tab-aware empty state copy (no saved searches / no view history).
	const renderEmptyTabState = () => {
		if (activeTab === "subscriptions") {
			return (
				<RootPage title="UCHAR" tabBarChildren={SearchHeaderContent} noPadding>
					{FilterDrawer}
					{HomeTabBar}
					<Container className="listings-container">
						<Center py={60}>
							<Stack align="center" gap="md">
								<Box
									style={{
										width: 80,
										height: 80,
										borderRadius: radii.full,
										backgroundColor: "#fff0f6",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconHeart size={36} color="#e64980" stroke={1.5} />
								</Box>
								<Text c="dimmed" size="sm" ta="center" maw={280}>
									{t("home.empty.subscriptions")}
								</Text>
							</Stack>
						</Center>
					</Container>
				</RootPage>
			);
		}
		if (activeTab === "recommended") {
			return (
				<RootPage title="UCHAR" tabBarChildren={SearchHeaderContent} noPadding>
					{FilterDrawer}
					{HomeTabBar}
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
								<Text c="dimmed" size="sm" ta="center" maw={280}>
									{t("home.empty.recommended")}
								</Text>
							</Stack>
						</Center>
					</Container>
				</RootPage>
			);
		}
		return null;
	};

	// Show skeletons while initial loading
	if (tabIsLoading && listings.length === 0) {
		return ShimmerSkeleton;
	}

	// Empty state — tab-specific copy for subscriptions / recommended.
	if (!tabIsLoading && listings.length === 0) {
		const tabEmpty = renderEmptyTabState();
		if (tabEmpty) return tabEmpty;
		return (
			<RootPage title="UCHAR" tabBarChildren={SearchHeaderContent} noPadding>
				{FilterDrawer}
				{HomeTabBar}
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
		<RootPage title="UCHAR" tabBarChildren={SearchHeaderContent} noPadding>
			{FilterDrawer}
			{HomeTabBar}
			<Container className="listings-container" px="md" pt="sm">
				{/* Block phase-2 — marketing banners (home_top placement) */}
				<HomeBanners placement="home_top" />
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
				{tabIsLoading && (
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
