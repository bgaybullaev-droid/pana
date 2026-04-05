import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Box,
	Container,
	LoadingOverlay,
	Text,
	Stack,
} from "@mantine/core";
import { IconHeart } from "@tabler/icons-react";
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
import { radii, surface } from "@app/styles/theme";
import {
	seedListingIds,
	seedListingSource,
} from "@modules/buyer/shared/state/model";

interface FavoritesPageProps {
	embedded?: boolean;
}

function Page({ embedded = false }: FavoritesPageProps) {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const { isAuthenticated } = useAuth();
	const [favorites, isLoading] = useUnit([$favorites, $isLoading]);
	const initializedRef = useRef(false);

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
		seedListingIds(favorites.map((f) => f.id));
		seedListingSource("finite");
		navigate(`/listings/${listingId}`);
	};

	if (!isAuthenticated) {
		if (embedded) {
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
				loginVariant="link"
			/>
		);
	}

	const content = (
		<>
			<LoadingOverlay visible={isLoading && favorites.length === 0} />
			<Container size={980} px="md" py="md">
				<Stack gap={10}>
					{favorites.length === 0 && !isLoading ? (
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
								{t("favorites.emptyTitle")}
							</Text>
							<Text c="dimmed" size="sm" mt={4}>
								{t("favorites.emptyDescription")}
							</Text>
						</Box>
					) : (
						favorites.map((listing) => (
							<FavoriteCard
								key={listing.id}
								listing={listing}
								onClick={() => handleCardClick(listing.id)}
								onRemove={(e) => handleRemove(e, listing.id)}
							/>
						))
					)}
				</Stack>
			</Container>
		</>
	);

	if (embedded) {
		return <Box style={{ backgroundColor: surface.page }}>{content}</Box>;
	}

	return (
		<RootPage
			title={t("favorites.title")}
			actions={
				favorites.length > 0 ? (
					<Box style={{ backgroundColor: "#228be6", borderRadius: 12, padding: "2px 8px" }}>
						<Text style={{ fontSize: 11, fontWeight: 700, color: "white", lineHeight: 1.4 }}>{favorites.length}</Text>
					</Box>
				) : undefined
			}
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
