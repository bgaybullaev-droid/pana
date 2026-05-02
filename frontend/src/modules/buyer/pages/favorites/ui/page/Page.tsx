import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Box,
	Container,
	LoadingOverlay,
	Text,
	Stack,
	TextInput,
	ActionIcon,
	ScrollArea,
	Tabs,
	Center,
	Loader,
} from "@mantine/core";
import { IconHeart, IconSearch, IconX } from "@tabler/icons-react";
import { RootPage } from "@shared/ui/RootPage";
import {
	$favorites,
	$isLoading,
	fetchFavorites,
	removeFavorite,
} from "../../model";
import { useAuth } from "@app/providers/useAuth";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import { FavoriteCard } from "../main/FavoriteCard";
import { SavedSearchCard } from "../main/SavedSearchCard";
import { radii, shadows, surface } from "@app/styles/theme";
import {
	seedListingIds,
	seedListingSource,
} from "@modules/buyer/shared/state/model";
import { translateDistrict } from "@shared/lib/regions";
import {
	$savedSearches,
	$savedSearchesLoading,
	fetchSavedSearchesFx,
	deleteSavedSearchFx,
	markSearchSeenFx,
} from "@modules/buyer/feature/saved-searches";
import { toggleSavedSearchNotifications } from "@modules/buyer/feature/saved-searches/model/events";
import { filtersChanged, type HomeFilters } from "../../../home/model";
import {
	searchQueryChanged,
	applyFilters,
} from "@modules/buyer/shared/state/model";

interface FavoritesPageProps {
	embedded?: boolean;
}

const ALL_PROPERTY_TYPES = ["apartment", "house", "commercial", "land"];

function Page({ embedded = false }: FavoritesPageProps) {
	const { t } = useTranslation("buyer");
	const { t: tSeller } = useTranslation("seller");
	const navigate = useNavigate();
	const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
	const [favorites, isLoading] = useUnit([$favorites, $isLoading]);
	const [savedSearches, savedSearchesLoading] = useUnit([
		$savedSearches,
		$savedSearchesLoading,
	]);
	const initializedRef = useRef(false);
	const searchesInitializedRef = useRef(false);

	const [activeTab, setActiveTab] = useState<string>("listings");
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPropertyType, setSelectedPropertyType] = useState<
		string | null
	>(null);

	const propertyTypeLabel = (type: string) => {
		const map: Record<string, string> = {
			apartment: tSeller("propertyTypes.apartment", "Apartments"),
			house: tSeller("propertyTypes.house", "Houses"),
			commercial: tSeller("propertyTypes.commercial", "Commercial"),
			land: tSeller("propertyTypes.land", "Land"),
		};
		return map[type] || type;
	};

	const filteredFavorites = useMemo(() => {
		return favorites.filter((l) => {
			if (selectedPropertyType && l.property_type !== selectedPropertyType)
				return false;
			if (searchQuery.trim() !== "") {
				const query = searchQuery.toLowerCase();
				const title = l.title ? l.title.toLowerCase() : "";
				const district = l.district
					? translateDistrict(l.district, tSeller).toLowerCase()
					: "";
				if (!title.includes(query) && !district.includes(query)) {
					return false;
				}
			}
			return true;
		});
	}, [favorites, selectedPropertyType, searchQuery, tSeller]);

	const propertyCounts = useMemo(() => {
		const counts: Record<string, number> = { all: favorites.length };
		ALL_PROPERTY_TYPES.forEach((type) => {
			counts[type] = 0;
		});
		favorites.forEach((l) => {
			if (l.property_type && counts[l.property_type] !== undefined) {
				counts[l.property_type]++;
			}
		});
		return counts;
	}, [favorites]);

	// Fetch favorites
	useEffect(() => {
		if (!isAuthenticated) return;
		if (initializedRef.current) return;
		initializedRef.current = true;
		fetchFavorites();
	}, [isAuthenticated]);

	// Fetch saved searches on mount so tab badge can show counts
	useEffect(() => {
		if (!isAuthenticated) return;
		if (searchesInitializedRef.current) return;
		searchesInitializedRef.current = true;
		fetchSavedSearchesFx();
	}, [isAuthenticated]);

	// Re-fetch saved searches when the page regains focus (back-navigation,
	// tab switch) so the new_count badge reflects listings created while the
	// user was away. Without this, the stale store (new_count=0) persists
	// until a full page reload.
	useEffect(() => {
		if (!isAuthenticated) return;
		const handleFocus = () => fetchSavedSearchesFx();
		window.addEventListener("focus", handleFocus);
		return () => window.removeEventListener("focus", handleFocus);
	}, [isAuthenticated]);

	const handleRemove = (e: React.MouseEvent, listingId: string) => {
		e.stopPropagation();
		removeFavorite(listingId);
	};

	const handleCardClick = (listingId: string) => {
		seedListingIds(filteredFavorites.map((f) => f.id));
		seedListingSource("finite");
		navigate(`/listings/${listingId}`);
	};

	const handleSearchCardClick = (searchId: string) => {
		const search = savedSearches.find((s) => s.id === searchId);
		if (!search) return;
		// Mark as seen (reset new_count)
		markSearchSeenFx(searchId);
		// Navigate to listings with the saved filters
		const params = new URLSearchParams();
		if (search.query) params.set("q", search.query);
		if (search.filters.deal_type) params.set("type", search.filters.deal_type);
		if (search.filters.property_type)
			params.set("property_type", search.filters.property_type);
		if (search.filters.rooms?.length) {
			search.filters.rooms.forEach((r) => params.append("rooms", String(r)));
		}
		if (search.filters.price_min != null)
			params.set("price_min", String(search.filters.price_min));
		if (search.filters.price_max != null)
			params.set("price_max", String(search.filters.price_max));
		if (search.filters.district)
			params.set("district", search.filters.district);
		if (search.filters.region) params.set("region", search.filters.region);

		// Apply the filters to effector immediately
		const urlFilters: Partial<HomeFilters> = {};
		if (search.query) urlFilters.q = search.query;
		if (search.filters.deal_type) urlFilters.type = [search.filters.deal_type];
		if (search.filters.property_type)
			urlFilters.property_type = [search.filters.property_type];
		if (search.filters.rooms?.length) urlFilters.rooms = search.filters.rooms;
		if (search.filters.price_min != null)
			urlFilters.price_min = search.filters.price_min;
		if (search.filters.price_max != null)
			urlFilters.price_max = search.filters.price_max;
		if (search.filters.district)
			urlFilters.district = [search.filters.district];
		if (search.filters.region) urlFilters.region = [search.filters.region];

		filtersChanged(urlFilters);
		if (search.query) {
			searchQueryChanged(search.query);
		} else {
			searchQueryChanged("");
		}

		// Force newest-first so new listings matching the saved filter
		// appear at the top of the results page.
		params.set("sort_by", "created_at");
		params.set("sort_order", "desc");

		applyFilters();

		navigate(`/?${params.toString()}`);
	};

	const handleDeleteSearch = (e: React.MouseEvent, searchId: string) => {
		e.stopPropagation();
		deleteSavedSearchFx(searchId);
	};

	const handleToggleNotifications = (
		e: React.MouseEvent,
		searchId: string,
		enabled: boolean,
	) => {
		e.stopPropagation();
		toggleSavedSearchNotifications({ id: searchId, enabled });
	};

	// ── Unauthenticated state ────────────────────────────────────────────────

	if (!isAuthenticated) {
		if (embedded) {
			if (isAuthLoading) {
				return (
					<Box ta="center" py={48} px="md" mih={200} pos="relative">
						<LoadingOverlay visible={true} />
					</Box>
				);
			}
			return (
				<Box ta="center" py={48} px="md">
					<Box
						style={{
							width: 80,
							height: 80,
							borderRadius: radii.full,
							backgroundColor: "#fff5f5",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							margin: "0 auto 16px",
						}}
					>
						<IconHeart size={36} color="#ffa8a8" stroke={1.5} />
					</Box>
					<Text fw={600} size="md">
						{t("favorites.loginPrompt")}
					</Text>
				</Box>
			);
		}
		return (
			<UnauthScreen
				icon={IconHeart}
				title={t("favorites.title")}
				subtitle={t("favorites.subtitle")}
				loginPrompt={t("favorites.loginPrompt")}
				loginLabel={t("common.login")}
				onLogin={() => navigate("/auth")}
				onBack={() => navigate(-1)}
			/>
		);
	}

	// ── Tab: Listings ────────────────────────────────────────────────────────

	const listingsContent = (
		<Stack gap={16}>
			{favorites.length > 0 && (
				<Box style={{ animation: "fade-in 0.4s ease-out" }}>
					<TextInput
						placeholder={t("search.title", "Search")}
						radius="xl"
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.currentTarget.value)}
						leftSection={<IconSearch size={20} color="#adb5bd" />}
						rightSection={
							searchQuery ? (
								<ActionIcon
									variant="filled"
									size={18}
									radius="50%"
									color="gray.5"
									onClick={() => setSearchQuery("")}
								>
									<IconX size={10} color="white" />
								</ActionIcon>
							) : null
						}
						styles={{
							input: {
								backgroundColor: "#ffffff",
								border: "1px solid #ced4da",
								boxShadow: shadows.md,
								height: 46,
							},
						}}
					/>

					<ScrollArea
						scrollbarSize={0}
						type="never"
						offsetScrollbars={false}
						mt={12}
					>
						<Box style={{ display: "flex", gap: 8 }}>
							<Box
								onClick={() => setSelectedPropertyType(null)}
								style={{
									padding: "5px 15px",
									borderRadius: radii.full,
									backgroundColor:
										selectedPropertyType === null ? "#228be6" : "#f1f3f5",
									border:
										selectedPropertyType === null
											? "1px solid #228be6"
											: "1px solid #ced4da",
									boxShadow: shadows.md,
									cursor: "pointer",
									whiteSpace: "nowrap",
									transition: "all 0.2s ease",
								}}
							>
								<Text
									size="xs"
									fw={600}
									c={selectedPropertyType === null ? "white" : "gray.7"}
								>
									{tSeller("listings.all", "All")} ({propertyCounts["all"]})
								</Text>
							</Box>
							{ALL_PROPERTY_TYPES.map((type) => {
								const isSelected = selectedPropertyType === type;
								return (
									<Box
										key={type}
										onClick={() => setSelectedPropertyType(type)}
										style={{
											padding: "5px 15px",
											borderRadius: radii.full,
											backgroundColor: isSelected ? "#228be6" : "#f1f3f5",
											border: isSelected
												? "1px solid #228be6"
												: "1px solid #ced4da",
											boxShadow: shadows.md,
											cursor: "pointer",
											whiteSpace: "nowrap",
											transition: "all 0.2s ease",
										}}
									>
										<Text
											size="xs"
											fw={600}
											c={isSelected ? "white" : "gray.7"}
										>
											{propertyTypeLabel(type)} ({propertyCounts[type]})
										</Text>
									</Box>
								);
							})}
						</Box>
					</ScrollArea>
				</Box>
			)}

			{filteredFavorites.length === 0 && !isLoading ? (
				<Box ta="center" py={48}>
					<Box
						style={{
							width: 80,
							height: 80,
							borderRadius: radii.full,
							backgroundColor: "#fff5f5",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							margin: "0 auto 16px",
						}}
					>
						<IconHeart size={36} color="#ffa8a8" stroke={1.5} />
					</Box>
					<Text fw={600} size="md">
						{searchQuery || selectedPropertyType
							? tSeller("listings.emptySearch", "No results found")
							: t("favorites.emptyTitle")}
					</Text>
					<Text c="dimmed" size="sm" mt={4}>
						{searchQuery || selectedPropertyType
							? ""
							: t("favorites.emptyDescription")}
					</Text>
				</Box>
			) : (
				<Stack gap={10}>
					{filteredFavorites.map((listing) => (
						<FavoriteCard
							key={listing.id}
							listing={listing}
							onClick={() => handleCardClick(listing.id)}
							onRemove={(e) => handleRemove(e, listing.id)}
						/>
					))}
				</Stack>
			)}
		</Stack>
	);

	// ── Tab: Saved Searches ──────────────────────────────────────────────────

	const searchesContent = (
		<>
			{savedSearchesLoading && savedSearches.length === 0 ? (
				<Center py={48}>
					<Loader size="md" color="blue" />
				</Center>
			) : savedSearches.length === 0 ? (
				<Box ta="center" py={48}>
					<Box
						style={{
							width: 80,
							height: 80,
							borderRadius: radii.full,
							backgroundColor: "#e7f5ff",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							margin: "0 auto 16px",
						}}
					>
						<IconSearch size={36} color="#74c0fc" stroke={1.5} />
					</Box>
					<Text fw={600} size="md">
						{t("favorites.searches.emptyTitle")}
					</Text>
					<Text c="dimmed" size="sm" mt={4}>
						{t("favorites.searches.emptyDescription")}
					</Text>
				</Box>
			) : (
				<Stack gap={10}>
					{savedSearches.map((search) => (
						<SavedSearchCard
							key={search.id}
							search={search}
							onClick={() => handleSearchCardClick(search.id)}
							onDelete={(e) => handleDeleteSearch(e, search.id)}
							onToggleNotifications={(e, enabled) =>
								handleToggleNotifications(e, search.id, enabled)
							}
						/>
					))}
				</Stack>
			)}
		</>
	);

	// ── Render ───────────────────────────────────────────────────────────────

	const content = (
		<>
			<LoadingOverlay visible={isLoading && favorites.length === 0} />
			<Container size={980} px="md" py="md">
				<Tabs
					value={activeTab}
					onChange={(v) => setActiveTab(v ?? "listings")}
					styles={{
						tab: { fontWeight: 600, fontSize: 14 },
						list: { marginBottom: 16, borderBottom: "2px solid #e9ecef" },
					}}
				>
					<Tabs.List grow justify="center">
						<Tabs.Tab value="listings">
							{t("favorites.tabListings")}
							{favorites.length > 0 && (
								<Box
									component="span"
									style={{
										marginLeft: 6,
										fontSize: 11,
										fontWeight: 700,
										backgroundColor: "#e9ecef",
										borderRadius: "10px",
										padding: "1px 7px",
										color: "#495057",
									}}
								>
									{favorites.length}
								</Box>
							)}
						</Tabs.Tab>
						<Tabs.Tab value="searches">
							{t("favorites.tabSearches")}
							{savedSearches.length > 0 && (
								<Box
									component="span"
									style={{
										marginLeft: 6,
										fontSize: 11,
										fontWeight: 700,
										backgroundColor: "#e9ecef",
										borderRadius: "10px",
										padding: "1px 7px",
										color: "#495057",
									}}
								>
									{savedSearches.length}
								</Box>
							)}
						</Tabs.Tab>
					</Tabs.List>

					<Tabs.Panel value="listings">{listingsContent}</Tabs.Panel>

					<Tabs.Panel value="searches">{searchesContent}</Tabs.Panel>
				</Tabs>
			</Container>

			<style>{`
				@keyframes fade-in {
					from { opacity: 0; }
					to { opacity: 1; }
				}
			`}</style>
		</>
	);

	if (embedded) {
		return <Box style={{ backgroundColor: surface.page }}>{content}</Box>;
	}

	return (
		<RootPage title={t("favorites.title")} noPadding>
			{content}
		</RootPage>
	);
}

export const Favorites = {
	route: "/favorites",
	Page,
};
