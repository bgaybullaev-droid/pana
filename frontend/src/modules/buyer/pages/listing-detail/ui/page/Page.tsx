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
	UnstyledButton,
} from "@mantine/core";
import { IconArrowLeft, IconPhoto } from "@tabler/icons-react";
import { shadows } from "@app/styles/theme";
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

	// Long-press the back button → toggle "clean mode": hide the info plate +
	// side rail across all mounted slides (a short tap still navigates back).
	// Reuses the shared "slide_show_info" flag + "slide-show-info" event that
	// every ListingSlideContent listens to.
	const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
	const longPressFired = useRef(false);

	const toggleCleanMode = useCallback(() => {
		const shown = sessionStorage.getItem("slide_show_info") !== "false";
		const next = !shown;
		sessionStorage.setItem("slide_show_info", String(next));
		window.dispatchEvent(new CustomEvent("slide-show-info", { detail: next }));
		webApp?.HapticFeedback.impactOccurred("medium");
	}, [webApp]);

	const startBackPress = useCallback(() => {
		longPressFired.current = false;
		longPressTimer.current = setTimeout(() => {
			longPressFired.current = true;
			toggleCleanMode();
		}, 450);
	}, [toggleCleanMode]);

	const cancelBackPress = useCallback(() => {
		if (longPressTimer.current) {
			clearTimeout(longPressTimer.current);
			longPressTimer.current = null;
		}
	}, []);

	const handleBack = useCallback(() => {
		if (longPressFired.current) {
			longPressFired.current = false;
			return;
		}
		navigate(-1);
	}, [navigate]);

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

			{/* Fixed back button */}
			<Box
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					paddingBottom: "env(safe-area-inset-bottom, 0px)",
					zIndex: 10000,
					pointerEvents: "none",
				}}
			>
				<Box
					style={{
						maxWidth: 500,
						margin: "0 auto",
						position: "relative",
						height: 72,
					}}
				>
					<UnstyledButton
						onClick={handleBack}
						onPointerDown={startBackPress}
						onPointerUp={cancelBackPress}
						onPointerLeave={cancelBackPress}
						onPointerCancel={cancelBackPress}
						onContextMenu={(e) => e.preventDefault()}
						aria-label={t("descriptionDrawer.back")}
						style={{
							position: "absolute",
							bottom: 12,
							right: 12,
							width: 56,
							height: 56,
							borderRadius: "50%",
							backgroundColor: "rgba(255, 255, 255, 0.65)",
							backdropFilter: "blur(20px) saturate(180%)",
							WebkitBackdropFilter: "blur(20px) saturate(180%)",
							border: "1px solid rgba(255, 255, 255, 0.5)",
							boxShadow: shadows.md,
							pointerEvents: "auto",
							userSelect: "none",
							touchAction: "manipulation",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<IconArrowLeft size={24} stroke={1.8} color="#495057" />
					</UnstyledButton>
				</Box>
			</Box>
		</Box>
	);
}

export const ListingDetail = {
	route: "/listings/:id",
	Page,
};
