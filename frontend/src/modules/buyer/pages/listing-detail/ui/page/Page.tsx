import { useEffect, useCallback, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { trackView, trackContact } from "@shared/lib/viewTracking";
import {
	ActionIcon,
	Box,
	LoadingOverlay,
	Text,
	Stack,
	Title,
	Button,
	Container,
	UnstyledButton,
} from "@mantine/core";
import { IconArrowLeft, IconBrandTelegram, IconPhone, IconPhoto } from "@tabler/icons-react";
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

	// Track the currently visible slide so the persistent contact buttons show
	// the active listing's phone / Telegram. Initialised to the route listing
	// (the slider scrolls there programmatically without firing the callback).
	const [activeId, setActiveId] = useState<string | null>(id ?? null);
	useEffect(() => {
		if (id) setActiveId(id);
	}, [id]);

	const handleVisibleItemChange = useCallback((visibleId: string) => {
		setActiveId(visibleId);
		ensureNearbyResolved(visibleId);
	}, []);

	// Mirror "clean mode" (toggled by long-pressing back) so the contact
	// buttons hide together with the rest of the chrome.
	const [showChrome, setShowChrome] = useState(
		() => sessionStorage.getItem("slide_show_info") !== "false",
	);
	useEffect(() => {
		const handler = (e: Event) => setShowChrome((e as CustomEvent).detail);
		window.addEventListener("slide-show-info", handler);
		return () => window.removeEventListener("slide-show-info", handler);
	}, []);

	const activeListing = activeId ? listingsMap[activeId] : undefined;

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
					onVisibleItemChange={handleVisibleItemChange}
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
							width: 45,
							height: 45,
							borderRadius: "50%",
							backgroundColor: "rgba(0, 0, 0, 0.6)",
							backdropFilter: "blur(20px) saturate(180%)",
							WebkitBackdropFilter: "blur(20px) saturate(180%)",
							border: "1px solid rgba(255, 255, 255, 0.25)",
							boxShadow: shadows.md,
							pointerEvents: "auto",
							userSelect: "none",
							touchAction: "manipulation",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<IconArrowLeft size={24} stroke={1.8} color="#fff" />
					</UnstyledButton>
				</Box>
			</Box>

			{/* Persistent contact CTA — call + write, stacked above the back
			    button and kept above the description drawer (zIndex 10002).
			    Uses the active slide's listing; hidden in clean mode and when
			    the listing has no phone / Telegram. */}
			{showChrome &&
				activeListing &&
				(activeListing.contact_phone || activeListing.seller_telegram) && (
				<Box
					style={{
						position: "fixed",
						bottom: 0,
						left: 0,
						right: 0,
						paddingBottom: "env(safe-area-inset-bottom, 0px)",
						zIndex: 10002,
						pointerEvents: "none",
					}}
				>
					<Box style={{ maxWidth: 500, margin: "0 auto", position: "relative", height: 200 }}>
						{/* Позвонить — fixed slot just above the back button */}
						{activeListing.contact_phone && (
							<ActionIcon
								component="a"
								href={`tel:${activeListing.contact_phone}`}
								onClick={() => void trackContact(activeListing.id)}
								variant="filled"
								color="green"
								radius="50%"
								size={45}
								aria-label={t("descriptionDrawer.call")}
								style={{ position: "absolute", bottom: 69, right: 12, pointerEvents: "auto", boxShadow: shadows.md }}
							>
								<IconPhone size={22} color="white" />
							</ActionIcon>
						)}
						{/* Написать — reserved slot above Позвонить; appears only with Telegram
						    so call/back never shift when it toggles. */}
						{activeListing.seller_telegram && (
							<ActionIcon
								component="a"
								href={`https://t.me/${activeListing.seller_telegram.replace(/^@/, "")}`}
								target="_blank"
								rel="noopener noreferrer"
								onClick={() => void trackContact(activeListing.id)}
								variant="filled"
								color="blue"
								radius="50%"
								size={45}
								aria-label={t("descriptionDrawer.telegram")}
								style={{ position: "absolute", bottom: 126, right: 12, pointerEvents: "auto", boxShadow: shadows.md }}
							>
								<IconBrandTelegram size={22} color="white" />
							</ActionIcon>
						)}
					</Box>
				</Box>
			)}
		</Box>
	);
}

export const ListingDetail = {
	route: "/listings/:id",
	Page,
};
