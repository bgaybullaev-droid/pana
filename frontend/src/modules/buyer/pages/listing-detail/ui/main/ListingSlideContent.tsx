import { FC, RefObject, useState, useEffect } from "react";
import {
	Box,
	Text,
	ActionIcon,
	Stack,
	Badge,
	Group,
	Transition,
	Avatar,
} from "@mantine/core";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination } from "swiper/modules";
import type { Swiper as SwiperType } from "swiper";
import {
	IconHeart,
	IconShare,
	IconUser,

	IconEye,
	IconMapPin,
	IconPhone,
	IconCheck,
	IconTrash,
	IconPhoto,
	IconShieldCheck,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import type { UnifiedListing } from "@shared/api/types";
import { useNavigate } from "react-router-dom";
import { formatPrice } from "@app/styles/theme";
import { translateDistrict, translateRegion } from "@shared/lib/regions";
import { trackContact } from "@shared/lib/viewTracking";
import { DescriptionDrawer } from "../dialogs/DescriptionDrawer";
import { MapDrawer } from "../dialogs/MapDrawer";

import "swiper/css";
import "swiper/css/pagination";

interface ListingSlideContentProps {
	listing: UnifiedListing;
	isActive: boolean;
	onLike?: (id: string) => void;
	onShare?: (id: string) => void;
	onCommentAdded?: (id: string) => void;
	onClaim?: (id: string) => void;
	onReject?: (id: string) => void;
	mode?: "buyer" | "seller-crawled";
	/**
	 * When provided, the description/map drawers render inside this element
	 * instead of the full viewport. Used by the seller Stage-2 preview so
	 * the drawers stay within the "phone screenshot" frame.
	 */
	containerRef?: RefObject<HTMLElement | null>;
}

const shadow = "0 1px 4px rgba(0,0,0,0.6)";

// market_type value → seller-namespace i18n key.
const MARKET_TYPE_KEY: Record<string, string> = {
	new: "createListing.marketTypeNew",
	secondary: "createListing.marketTypeSecondary",
};

// condition value → seller-namespace i18n key.
const CONDITION_KEY: Record<string, string> = {
	euro: "createListing.condEuro",
	cosmetic: "createListing.condCosmetic",
	needs_repair: "createListing.condRepair",
	rough: "createListing.condRough",
	none: "createListing.condNone",
	shell: "createListing.condShell",
	medium: "createListing.condMedium",
	designer: "createListing.condDesigner",
	turnkey: "createListing.condTurnkey",
	needs_repair_comm: "createListing.condNeedsRepairComm",
};

// Compact relative "published N days ago" label for the card.
function formatRelativeDate(iso: string, t: TFunction): string {
	const diffMs = Date.now() - new Date(iso).getTime();
	const days = Math.floor(diffMs / 86_400_000);
	if (days <= 0) return t("listing.today");
	if (days === 1) return t("listing.yesterday");
	if (days < 30) return t("listing.daysAgoShort", { count: days });
	if (days < 365) return t("listing.monthsAgoShort", { count: Math.floor(days / 30) });
	return t("listing.yearsAgoShort", { count: Math.floor(days / 365) });
}

export const ListingSlideContent: FC<ListingSlideContentProps> = ({
	listing,
	isActive,
	onLike,
	onShare,
	onCommentAdded,
	onClaim,
	onReject,
	mode = "buyer",
	containerRef,
}) => {
	const { t } = useTranslation("buyer");
	const navigate = useNavigate();
	const [showInfo, setShowInfo] = useState(
		() => sessionStorage.getItem("slide_show_info") !== "false",
	);
	const [descriptionOpen, setDescriptionOpen] = useState(false);
	const [mapOpen, setMapOpen] = useState(false);
	const [failedImages, setFailedImages] = useState<number[]>([]);

	const handleImageError = (index: number) => {
		setFailedImages((prev) => [...prev, index]);
	};
const [swiperInstance, setSwiperInstance] = useState<SwiperType | null>(null);

	// Explicit keyboard support for horizontal swiping
	useEffect(() => {
		if (!isActive || !swiperInstance) return;

		const handleKeyDown = (e: KeyboardEvent) => {
			const tagName = document.activeElement?.tagName;
			if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
				return;
			}
			if (e.key === "ArrowLeft") {
				e.preventDefault();
				swiperInstance.slidePrev();
			} else if (e.key === "ArrowRight") {
				e.preventDefault();
				swiperInstance.slideNext();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isActive, swiperInstance]);

	useEffect(() => {
		const handler = (e: Event) => setShowInfo((e as CustomEvent).detail);
		window.addEventListener("slide-show-info", handler);
		return () => window.removeEventListener("slide-show-info", handler);
	}, []);

	const formattedPrice = formatPrice(listing.price, listing.currency);
	const districtLabel =
		translateDistrict(listing.district, t) || t("listing.defaultDistrict");
	const regionLabel = listing.region ? translateRegion(listing.region, t) : null;
	const sellerDisplayName = listing.seller_name || null;

	// Seller-namespace translation (enum labels live in the seller bundle).
	const ts = (key: string, fallback?: string) =>
		t(key, { ns: "seller", defaultValue: fallback ?? key });

	const sellerTypeLabel = listing.seller_type
		? t(`descriptionDrawer.sellerType.${listing.seller_type}`, listing.seller_type)
		: null;
	const dateLabel = formatRelativeDate(listing.created_at, t);
	const marketTypeLabel =
		listing.market_type && MARKET_TYPE_KEY[listing.market_type]
			? ts(MARKET_TYPE_KEY[listing.market_type], listing.market_type)
			: null;
	const conditionLabel =
		listing.condition && CONDITION_KEY[listing.condition]
			? ts(CONDITION_KEY[listing.condition], listing.condition)
			: null;
	// Price per m² — prefer the explicit field, else derive from price / area.
	const pricePerSqm =
		listing.price_per_sqm ??
		(listing.area && listing.area > 0
			? Math.round(listing.price / listing.area)
			: null);

	return (
		<Box
			style={{
				height: "100%",
				width: "100%",
				position: "relative",
				background: "#000",
			}}
		>
			{/* ── Horizontal Image Swiper (full screen background) ── */}
			{listing.images.length > 0 ? (
				<Swiper
					onSwiper={setSwiperInstance}
					pagination={{ dynamicBullets: true }}
					modules={[Pagination]}
					style={{ height: "100%", width: "100%" }}
					className="listing-detail-swiper"
				>
					{listing.images.map((image, index) => (
						<SwiperSlide key={index}>
							{!failedImages.includes(index) ? (
								<img
									src={image.url}
									alt={listing.title || listing.description || "Listing image"}
									loading={isActive && index === 0 ? "eager" : "lazy"}
									decoding="async"
									style={{ width: "100%", height: "100%", objectFit: "cover" }}
									onError={() => handleImageError(index)}
								/>
							) : (
								<Box
									style={{
										width: "100%",
										height: "100%",
										display: "flex",
										flexDirection: "column",
										alignItems: "center",
										justifyContent: "center",
										background: "#1a1a1a",
										gap: 12,
									}}
								>
									<IconPhoto size={48} color="#444" />
									<Text c="dimmed" size="sm">
										{t("listing.imageLoadError")}
									</Text>
								</Box>
							)}
						</SwiperSlide>
					))}
				</Swiper>
			) : (
				<Box
					style={{
						width: "100%",
						height: "100%",
						display: "flex",
						flexDirection: "column",
						alignItems: "center",
						justifyContent: "center",
						background: "#1a1a1a",
						gap: 16,
					}}
				>
					<IconPhoto size={64} color="#333" />
					<Text c="dimmed" fw={500}>
						{t("listing.noImages")}
					</Text>
				</Box>
			)}

			{/* ── Gradient Overlay ── */}
			<Transition mounted={showInfo} transition="fade" duration={300}>
				{(styles) => (
					<Box
						pos="absolute"
						bottom={0}
						left={0}
						right={0}
						w="100%"
						h="50vh"
						style={{
							...styles,
							pointerEvents: "none",
							background:
								"linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.85) 65%)",
							zIndex: 9,
						}}
					/>
				)}
			</Transition>

			{/* ── Right side action buttons (TikTok-style) — fade out together with
			     the info plate in "clean mode" (long-press the back button). ── */}
			<Box
				style={{
					zIndex: 50,
					position: "absolute",
					bottom: "calc(env(safe-area-inset-bottom, 0px) + 120px)",
					right: 12,
					width: 56,
					opacity: showInfo ? 1 : 0,
					pointerEvents: showInfo ? "auto" : "none",
					transition: "opacity 300ms ease",
				}}
			>
				<Stack gap={18} align="center">
					{mode === "buyer" ? (
						<Stack gap={1} align="center">
							<ActionIcon
								variant="transparent"
								size={36}
								onClick={() => onLike?.(listing.id)}
							>
								<IconHeart
									size={30}
									fill={listing.is_favorited ? "red" : "none"}
									color={listing.is_favorited ? "red" : "white"}
									style={{ filter: `drop-shadow(${shadow})` }}
								/>
							</ActionIcon>
						</Stack>
					) : (
						<Stack gap={18} align="center">
							<Stack gap={1} align="center">
								<ActionIcon
									variant="transparent"
									size={36}
									onClick={() => onClaim?.(listing.id)}
								>
									<IconCheck
										size={30}
										color="#4dabf7"
										style={{ filter: `drop-shadow(${shadow})` }}
									/>
								</ActionIcon>
								<Text size="xs" fw={700} c="#4dabf7" style={{ textShadow: shadow }}>
									{t("listingDetail.claimMine")}
								</Text>
							</Stack>
							<Stack gap={1} align="center">
								<ActionIcon
									variant="transparent"
									size={36}
									onClick={() => onReject?.(listing.id)}
								>
									<IconTrash
										size={30}
										color="#ff8787"
										style={{ filter: `drop-shadow(${shadow})` }}
									/>
								</ActionIcon>
								<Text size="xs" fw={700} c="#ff8787" style={{ textShadow: shadow }}>
									{t("listingDetail.claimNotMine")}
								</Text>
							</Stack>
						</Stack>
					)}

					{/* Map */}
					<Stack gap={1} align="center">
						<ActionIcon
							variant="transparent"
							size={36}
							onClick={() => setMapOpen(true)}
						>
							<IconMapPin
								size={28}
								color="white"
								style={{ filter: `drop-shadow(${shadow})` }}
							/>
						</ActionIcon>
					</Stack>

					{/* Phone — crawled preview keeps the plain icon; buyer uses the CTA block below */}
					{mode !== "buyer" && listing.contact_phone && (
						<Stack gap={1} align="center">
							<ActionIcon
								variant="transparent"
								size={36}
								onClick={() => {
									// Telemetry first (fire-and-forget) so the
									// contacts_count bump is recorded even if the
									// tel: navigation tears the page down.
									void trackContact(listing.id);
									window.location.href = `tel:${listing.contact_phone}`;
								}}
							>
								<IconPhone
									size={28}
									color="white"
									style={{ filter: `drop-shadow(${shadow})` }}
								/>
							</ActionIcon>
						</Stack>
					)}

					{/* Share */}
					{mode === "buyer" && (
						<Stack gap={1} align="center">
							<ActionIcon
								variant="transparent"
								size={36}
								onClick={() => onShare?.(listing.id)}
							>
								<IconShare
									size={28}
									color="white"
									style={{ filter: `drop-shadow(${shadow})` }}
								/>
							</ActionIcon>
						</Stack>
					)}

				</Stack>
			</Box>


			{/* ── Bottom-left — Product Info ── */}
			<Box
				pos="absolute"
				left={0}
				right={80}
				style={{ zIndex: 10, bottom: "calc(env(safe-area-inset-bottom, 0px) + 24px)" }}
				px={12}
			>
				<Transition mounted={showInfo} transition="fade" duration={300}>
					{(styles) => (
						<Stack gap={6} style={styles}>
							{/* Seller avatar + name + verified + type · date */}
							<Group
								gap={8}
								align="center"
								wrap="nowrap"
								style={{ cursor: listing.seller_id ? "pointer" : "default" }}
								onClick={() => {
									if (listing.seller_id)
										navigate(`/seller/${listing.seller_id}`);
								}}
							>
								<Avatar
									src={listing.seller_avatar_url}
									size={36}
									radius={18}
									color="gray.7"
									styles={{
										root: {
											border: "2px solid #fff",
											backgroundColor: "rgba(0,0,0,0.3)",
										},
										image: { objectFit: "cover" },
									}}
								>
									<IconUser size={18} color="white" />
								</Avatar>
								<Box style={{ minWidth: 0 }}>
									<Group gap={4} wrap="nowrap" align="center">
										{sellerDisplayName && (
											<Text
												size="sm"
												fw={700}
												c="white"
												truncate
												style={{ textShadow: shadow }}
											>
												@{sellerDisplayName}
											</Text>
										)}
										{listing.seller_verified && (
											<IconShieldCheck
												size={15}
												color="#4dabf7"
												style={{
													flexShrink: 0,
													filter: `drop-shadow(${shadow})`,
												}}
											/>
										)}
									</Group>
									{(sellerTypeLabel || dateLabel) && (
										<Group gap={6} wrap="nowrap" align="center">
											<Text
												size="11px"
												c="rgba(255,255,255,0.85)"
												truncate
												style={{ textShadow: shadow }}
											>
												{[sellerTypeLabel, dateLabel]
													.filter(Boolean)
													.join(" · ")}
											</Text>
											<Group gap={3} wrap="nowrap" align="center" style={{ flexShrink: 0 }}>
												<IconEye
													size={13}
													color="rgba(255,255,255,0.85)"
													style={{ filter: `drop-shadow(${shadow})` }}
												/>
												<Text
													size="11px"
													c="rgba(255,255,255,0.85)"
													style={{ textShadow: shadow }}
												>
													{listing.views_count || 0}
												</Text>
											</Group>
										</Group>
									)}
								</Box>
							</Group>

							{/* Tappable info block — opens the description drawer */}
							<Box
								onClick={() => setDescriptionOpen(true)}
								style={{
									cursor: "pointer",
									display: "flex",
									flexDirection: "column",
									gap: 6,
								}}
							>
								{/* Row 1 — type + deal type (+ urgent) */}
								<Group gap={4} wrap="wrap">
									{listing.urgent_flag && (
										<Badge size="xs" variant="filled" color="red" radius="sm">
											{t("listing.badges.urgent").toUpperCase()}
										</Badge>
									)}
									<Badge
										size="xs"
										variant="filled"
										color={listing.type === "sell" ? "blue" : "green"}
										radius="sm"
									>
										{listing.property_type === "apartment"
											? t("card.propertyType.apartment").toUpperCase()
											: listing.property_type === "house"
												? t("card.propertyType.house").toUpperCase()
												: listing.property_type === "commercial"
													? t("card.propertyType.commercial").toUpperCase()
													: t("card.propertyType.land").toUpperCase()}
									</Badge>
									<Badge
										size="xs"
										variant="filled"
										color={listing.type === "sell" ? "blue" : "green"}
										radius="sm"
									>
										{listing.type === "sell"
											? t("listing.typeSell").toUpperCase()
											: t("listing.typeRent").toUpperCase()}
									</Badge>
								</Group>

								{/* Row 2 — size: area, rooms, floor */}
								{(listing.area != null ||
									listing.rooms != null ||
									listing.floor != null) && (
									<Group gap={4} wrap="wrap">
										{listing.area != null && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{listing.area} {t("listing.area")}
											</Badge>
										)}
										{listing.rooms != null && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{listing.rooms} {t("listing.rooms")}
											</Badge>
										)}
										{listing.floor != null && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{listing.floor}/{listing.total_floors || "?"}
											</Badge>
										)}
									</Group>
								)}

								{/* Row 3 — qualitative: market type, condition, ЖК */}
								{(marketTypeLabel || conditionLabel || listing.jk_name) && (
									<Group gap={4} wrap="wrap">
										{marketTypeLabel && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{marketTypeLabel.toUpperCase()}
											</Badge>
										)}
										{conditionLabel && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{conditionLabel.toUpperCase()}
											</Badge>
										)}
										{listing.jk_name && (
											<Badge size="xs" variant="filled" color="gray" radius="sm">
												{listing.jk_name}
											</Badge>
										)}
									</Group>
								)}

								{/* Finance perks — mortgage / installment / halal.
								    Main listings only; crawled sources default false. */}
								{(listing.mortgage_ok ||
									listing.installment_ok ||
									listing.halol_ok) && (
									<Group gap={4} wrap="wrap">
										{listing.mortgage_ok && (
											<Badge size="xs" variant="filled" color="teal" radius="sm">
												{t("listing.badges.mortgage")}
											</Badge>
										)}
										{listing.installment_ok && (
											<Badge size="xs" variant="filled" color="teal" radius="sm">
												{t("listing.badges.installment")}
											</Badge>
										)}
										{listing.halol_ok && (
											<Badge size="xs" variant="filled" color="teal" radius="sm">
												{t("listing.badges.halol")}
											</Badge>
										)}
									</Group>
								)}

								{/* Location — region + district + metro */}
								<Group gap={4} wrap="wrap">
									{regionLabel && (
										<Badge size="xs" variant="filled" color="gray" radius="sm">
											{regionLabel.toUpperCase()}
										</Badge>
									)}
									<Badge size="xs" variant="filled" color="gray" radius="sm">
										{districtLabel.toUpperCase()}
									</Badge>
									{listing.metro_station && (
										<Badge size="xs" variant="filled" color="gray" radius="sm">
											м. {ts(`createListing.metroStation.${listing.metro_station}`, listing.metro_station)}
										</Badge>
									)}
								</Group>

								{/* Price + price per m² + negotiable */}
								<Group gap={8} align="baseline" wrap="wrap">
									<Text
										size="xl"
										fw={800}
										c="white"
										style={{ textShadow: "0 2px 6px rgba(0,0,0,0.6)" }}
									>
										{formattedPrice}
									</Text>
									{pricePerSqm != null && (
										<Text
											size="xs"
											fw={600}
											c="rgba(255,255,255,0.9)"
											style={{ textShadow: shadow }}
										>
											{formatPrice(pricePerSqm, listing.currency)}/
											{t("listing.area")}
										</Text>
									)}
									{listing.is_negotiable && (
										<Badge size="xs" variant="filled" color="green" radius="sm">
											{t("listing.badges.negotiable")}
										</Badge>
									)}
								</Group>
							</Box>
						</Stack>
					)}
				</Transition>
			</Box>

			{/* ── Description Drawer ── */}
			<DescriptionDrawer
				opened={descriptionOpen}
				onClose={() => setDescriptionOpen(false)}
				listing={listing}
				onCommentAdded={() => onCommentAdded?.(listing.id)}
				container={containerRef?.current}
			/>

			{/* ── Map Drawer ── */}
			<MapDrawer
				opened={mapOpen}
				onClose={() => setMapOpen(false)}
				listing={listing}
				container={containerRef?.current}
			/>
		</Box>
	);
};
