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
import { radii, shadows, surface } from "@app/styles/theme";
import {
	seedListingIds,
	seedListingSource,
} from "@modules/buyer/shared/state/model";
import { translateDistrict } from "@shared/lib/regions";

interface FavoritesPageProps {
	embedded?: boolean;
}

const ALL_PROPERTY_TYPES = ['apartment', 'house', 'commercial', 'land'];

function Page({ embedded = false }: FavoritesPageProps) {
	const { t } = useTranslation("buyer");
	const { t: tSeller } = useTranslation("seller");
	const navigate = useNavigate();
	const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
	const [favorites, isLoading] = useUnit([$favorites, $isLoading]);
	const initializedRef = useRef(false);

	const [searchQuery, setSearchQuery] = useState('');
	const [selectedPropertyType, setSelectedPropertyType] = useState<string | null>(null);

	const propertyTypeLabel = (type: string) => {
		const map: Record<string, string> = {
			apartment: tSeller('propertyTypes.apartment', 'Apartments'),
			house: tSeller('propertyTypes.house', 'Houses'),
			commercial: tSeller('propertyTypes.commercial', 'Commercial'),
			land: tSeller('propertyTypes.land', 'Land'),
		};
		return map[type] || type;
	};

	const filteredFavorites = useMemo(() => {
		return favorites.filter((l) => {
			// Filter by property type
			if (selectedPropertyType && l.property_type !== selectedPropertyType) return false;

			// Filter by search query
			if (searchQuery.trim() !== '') {
				const query = searchQuery.toLowerCase();
				const title = l.title ? l.title.toLowerCase() : '';
				const district = l.district ? translateDistrict(l.district, tSeller).toLowerCase() : '';

				if (!title.includes(query) && !district.includes(query)) {
					return false;
				}
			}

			return true;
		});
	}, [favorites, selectedPropertyType, searchQuery, tSeller]);

	const propertyCounts = useMemo(() => {
		const counts: Record<string, number> = { all: favorites.length };
		ALL_PROPERTY_TYPES.forEach(type => {
			counts[type] = 0;
		});

		favorites.forEach((l) => {
			if (l.property_type && counts[l.property_type] !== undefined) {
				counts[l.property_type]++;
			}
		});
		return counts;
	}, [favorites]);

	useEffect(() => {
		if (!isAuthenticated) return;
		if (initializedRef.current) return;
		initializedRef.current = true;
		fetchFavorites();
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

	if (!isAuthenticated) {
		if (embedded) {
			if (isAuthLoading) {
				return <Box ta="center" py={48} px="md" mih={200} pos="relative"><LoadingOverlay visible={true} /></Box>;
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

	const content = (
		<>
			<LoadingOverlay visible={isLoading && favorites.length === 0} />
			<Container size={980} px="md" py="md">
				<Stack gap={16}>
					{/* ── Search and Filters ── */}
					{favorites.length > 0 && (
						<Box style={{ animation: 'fade-in 0.4s ease-out' }}>
							<TextInput
								placeholder={t('search.title', 'Search')}
								radius="xl"
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.currentTarget.value)}
								leftSection={<IconSearch size={20} color="#adb5bd" />}
								rightSection={
									searchQuery ? (
										<ActionIcon variant="filled" size={18} radius="50%" color="gray.5" onClick={() => setSearchQuery('')}>
											<IconX size={10} color="white" />
										</ActionIcon>
									) : null
								}
								styles={{
									input: {
										backgroundColor: '#ffffff',
										border: '1px solid #ced4da',
										boxShadow: shadows.md,
										height: 46,
									}
								}}
							/>

							<ScrollArea scrollbarSize={0} type="never" offsetScrollbars={false} mt={12}>
								<Box style={{ display: "flex", gap: 8 }}>
									<Box
										onClick={() => setSelectedPropertyType(null)}
										style={{
											padding: "5px 15px",
											borderRadius: radii.full,
											backgroundColor: selectedPropertyType === null ? "#228be6" : "#f1f3f5",
											border: selectedPropertyType === null ? "1px solid #228be6" : "1px solid #ced4da",
											boxShadow: shadows.md,
											cursor: "pointer",
											whiteSpace: "nowrap",
											transition: "all 0.2s ease",
										}}
									>
										<Text size="xs" fw={600} c={selectedPropertyType === null ? "white" : "gray.7"}>
											{tSeller('listings.all', 'All')} ({propertyCounts['all']})
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
													border: isSelected ? "1px solid #228be6" : "1px solid #ced4da",
													boxShadow: shadows.md,
													cursor: "pointer",
													whiteSpace: "nowrap",
													transition: "all 0.2s ease",
												}}
											>
												<Text size="xs" fw={600} c={isSelected ? "white" : "gray.7"}>
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
								{searchQuery || selectedPropertyType ? tSeller('listings.emptySearch', 'No results found') : t("favorites.emptyTitle")}
							</Text>
							<Text c="dimmed" size="sm" mt={4}>
								{searchQuery || selectedPropertyType ? '' : t("favorites.emptyDescription")}
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
		<RootPage
			title={t("favorites.title")}
			noPadding
		>
			{content}
		</RootPage>
	);
}

export const Favorites = {
	route: "/favorites",
	Page,
};
