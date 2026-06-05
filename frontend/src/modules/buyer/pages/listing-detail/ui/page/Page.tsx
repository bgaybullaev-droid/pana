import { useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { trackView } from "@shared/lib/viewTracking";
import {
	Box,
	LoadingOverlay,
	Text,
	Stack,
	Title,
	Button,
	Container,
} from "@mantine/core";
import { IconPhoto } from "@tabler/icons-react";
import { useTelegram } from "@app/providers/useTelegram";
import { useAuth } from "@app/providers/useAuth";
import { getListingShareUrl } from "@shared/lib/constants";
import { ListingTikTokSlider } from "../main/ListingTikTokSlider";
import {
	$slideIds,
	$listingsMap,
	$isLoading,
	$hasMore,
	$error,
	pageOpened,
	loadMore,
	toggleFavorite,
	ensureNearbyResolved,
} from "../../model";

// UUID validation helper
const isValidUUID = (str: string): boolean => {
	const uuidRegex =
		/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
	return uuidRegex.test(str);
};

function Page() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const { t } = useTranslation("buyer");
	const { webApp } = useTelegram();
	const { isAuthenticated } = useAuth();
	const [slideIds, listingsMap, isLoading, hasMore, error] = useUnit([
		$slideIds,
		$listingsMap,
		$isLoading,
		$hasMore,
		$error,
	]);
	const initializedRef = useRef<string | null>(null);

	// Validate UUID and fetch data
	useEffect(() => {
		if (id && !isValidUUID(id)) {
			navigate("/", { replace: true });
			return;
		}
		// Prevent double call in React StrictMode
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			pageOpened(id);
		}
	}, [id, navigate]);

	// Per-user view event with dwell — fires immediately on mount with
	// dwell=null, then a follow-up on unmount/page-hide with the elapsed
	// time. Skipped for anonymous users (server requires auth).
	useEffect(() => {
		if (!id || !isValidUUID(id)) return;
		return trackView(id, isAuthenticated);
	}, [id, isAuthenticated]);

	const handleLike = useCallback(
		(listingId: string) => {
			if (!isAuthenticated) {
				navigate("/auth");
				return;
			}
			webApp?.HapticFeedback.impactOccurred("light");
			toggleFavorite(listingId);
		},
		[isAuthenticated, navigate, webApp],
	);

	const handleShare = useCallback(
		(listingId: string) => {
			webApp?.HapticFeedback.impactOccurred("light");
			webApp?.openTelegramLink(getListingShareUrl(listingId));
		},
		[webApp],
	);

	if (isLoading && slideIds.length === 0) {
		return <LoadingOverlay visible />;
	}

	if (error) {
		return (
			<Container size={980} px="md" py="xl">
				<Stack align="center" gap="md">
					<IconPhoto size={64} color="var(--mantine-color-gray-5)" />
					<Title order={3} ta="center">
						{t("listingDetail.notFound")}
					</Title>
					<Text c="dimmed" ta="center">
						{error || t("listingDetail.notFoundDescription")}
					</Text>
					<Button variant="light" onClick={() => navigate("/")}>
						{t("listingDetail.goHome")}
					</Button>
				</Stack>
			</Container>
		);
	}

	return (
		<Box className="dynamic-screen-height" w="100%" pos="relative" style={{ overflow: "hidden" }}>
			{/* TikTok Slider */}
			{id && slideIds.length > 0 && (
				<ListingTikTokSlider
					slideIds={slideIds}
					listingsMap={listingsMap}
					initialListingId={id}
					onLoadMore={loadMore}
					hasMore={hasMore}
					onLike={handleLike}
					onShare={handleShare}
					onVisibleItemChange={ensureNearbyResolved}
				/>
			)}

		</Box>
	);
}

export const ListingDetail = {
	route: "/listings/:id",
	Page,
};
