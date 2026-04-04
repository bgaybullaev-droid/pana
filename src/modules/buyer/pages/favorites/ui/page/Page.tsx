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
	Group,
	Badge,
	ActionIcon,
} from "@mantine/core";
import { IconHeart, IconArrowLeft } from "@tabler/icons-react";
import {
	$favorites,
	$isLoading,
	fetchFavorites,
	removeFavorite,
} from "../../model";
import { useAuth } from "@app/providers/useAuth";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import { FavoriteCard } from "../main/FavoriteCard";
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
							borderRadius: "50%",
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
			<Container size="sm" px="md" py="md">
				<Stack gap={10}>
					{favorites.length === 0 && !isLoading ? (
						<Box ta="center" py={48}>
							<Box
								style={{
									width: 80,
									height: 80,
									borderRadius: "50%",
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
		return <Box bg="#f8f9fa">{content}</Box>;
	}

	return (
		<Box mih="100vh" bg="#f8f9fa">
			{/* Header */}
			<Box
				style={{
					backgroundColor: "white",
					padding: "12px 16px",
					borderBottom: "1px solid rgba(0,0,0,0.06)",
				}}
			>
				<Group justify="space-between" align="center">
					<Group gap={8}>
						<ActionIcon
							variant="subtle"
							color="gray"
							size={36}
							radius={12}
							onClick={() => navigate(-1)}
						>
							<IconArrowLeft size={20} />
						</ActionIcon>
						<Text
							size="lg"
							fw={700}
							style={{ fontFamily: "var(--mantine-font-family-headings)" }}
						>
							{t("favorites.title")}
						</Text>
					</Group>
					<Badge
						size="lg"
						radius={10}
						variant="light"
						color="blue"
						style={{ fontWeight: 700 }}
					>
						{favorites.length}
					</Badge>
				</Group>
			</Box>
			{content}
		</Box>
	);
}

export const Favorites = {
	route: "/favorites",
	Page,
};
