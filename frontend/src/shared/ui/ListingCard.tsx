import { FC, useState } from "react";
import { Text, Skeleton, UnstyledButton, Box, ActionIcon } from "@mantine/core";
import {
	IconHeart,
	IconBed,
	IconRuler,
	IconBuilding,
	IconMapPin,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { ListingListItem } from "@shared/api/types";
import {
	formatPrice,
	gradients,
	radii,
	shadows,
	spacing,
	surface,
} from "@app/styles/theme";
import {
	translateDistrict,
	translateRegion,
	getRegionForDistrict,
} from "@shared/lib/regions";
import {
	getListingCardContent,
	type CardStatusBadgeType,
} from "./listing-card/adapter";
import type { FieldKey } from "@modules/seller/feature/listing-form/lib/visibility";

interface ListingCardProps {
	listing: ListingListItem;
	onClick: (id: string) => void;
	isFavorited?: boolean;
	onFavorite?: (id: string) => void;
	layout?: "grid" | "masonry";
}

// Icon mapping for chip fields (T-020). The card renders whatever chips
// the adapter returns — it does NOT decide visibility itself.
const CHIP_ICON: Partial<Record<FieldKey, typeof IconBed>> = {
	rooms: IconBed,
	area: IconRuler,
	floor: IconBuilding,
	land_area: IconRuler,
};

// T-021 — purely a styling table. Card has zero logic; if the adapter
// emits a badge type that isn't in this map, we fall back to neutral grey.
const BADGE_BG: Record<CardStatusBadgeType, string> = {
	urgent: "rgba(250,82,82,0.92)", // red — "СРОЧНО"
	verified: "rgba(18,184,134,0.92)", // teal — "Проверенный"
};

export const ListingCard: FC<ListingCardProps> = ({
	listing,
	onClick,
	isFavorited,
	onFavorite,
	layout = "grid",
}) => {
	const { t } = useTranslation("buyer");
	const [imageLoaded, setImageLoaded] = useState(false);

	// All variant-specific rendering is derived by the adapter, which reads
	// the visibility matrix as its single source of truth. The card
	// component never branches on listing.type / listing.property_type for
	// field visibility.
	const cardContent = getListingCardContent(listing, t);
	const formattedPrice = formatPrice(listing.price, listing.currency, {
		period: cardContent.price.period,
	});

	const propertyLabel = t(
		`card.propertyType.${listing.property_type}`,
		t(`common.propertyType.${listing.property_type}`, listing.property_type),
	);

	let actualRegionKey = listing.region;
	if (!actualRegionKey && listing.district) {
		actualRegionKey = getRegionForDistrict(listing.district) || null;
	}

	const regionLabel = translateRegion(actualRegionKey, t);
	const districtRawLabel = translateDistrict(listing.district, t);

	const locationParts = [];
	if (regionLabel && regionLabel !== districtRawLabel) {
		locationParts.push(regionLabel);
	}
	if (districtRawLabel) {
		locationParts.push(districtRawLabel);
	}

	const fullLocationLabel =
		locationParts.length > 0
			? locationParts.join(", ")
			: t("listing.defaultDistrict");

	// Title suffix uses the matrix-derived tagLine to decide whether a
	// building-type subtitle is available — no hardcoded property_type
	// check. We take the first tag if present (typically building_type on
	// apartments) to keep the pre-PR5 suffix UX.
	const titleSuffix = cardContent.tagLine
		? `, ${cardContent.tagLine.split(",")[0].toLowerCase()}`
		: "";

	const standardTitle = `${propertyLabel}${titleSuffix}, ${fullLocationLabel}`;
	const tagLine = cardContent.tagLine ?? "";

	// Deterministic varied height for masonry based on listing id
	const masonryHeight =
		layout === "masonry"
			? [160, 200, 240, 180, 220][
					(listing.id.charCodeAt(0) + listing.id.charCodeAt(1)) % 5
				]
			: 180;

	return (
		<UnstyledButton
			onClick={() => onClick(listing.id)}
			style={{ width: "100%", minWidth: 0, display: "block" }}
		>
			<Box
				style={{
					borderRadius: radii.lg,
					overflow: "hidden",
					backgroundColor: surface.card,
					boxShadow: shadows.md,
				}}
			>
				{/* Image */}
				<Box style={{ position: "relative", lineHeight: 0 }}>
					{!imageLoaded && listing.primary_image_url && (
						<Skeleton
							height={masonryHeight}
							radius={0}
							animate
							style={{
								position: "absolute",
								top: 0,
								left: 0,
								right: 0,
								zIndex: 1,
							}}
						/>
					)}

					{listing.primary_image_url ? (
						<img
							src={listing.primary_image_url}
							alt={standardTitle}
							loading="lazy"
							style={{
								display: "block",
								width: "100%",
								height: masonryHeight,
								objectFit: "cover" as const,
								opacity: imageLoaded ? 1 : 0,
								transition: "opacity 0.3s ease",
							}}
							onLoad={() => setImageLoaded(true)}
						/>
					) : (
						<Box
							h={masonryHeight}
							bg="gray.1"
							style={{
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
							}}
						>
							<Text size="xs" c="dimmed">
								{t("common.noImage")}
							</Text>
						</Box>
					)}

					{/* Gradient overlay */}
					<Box
						style={{
							position: "absolute",
							bottom: 0,
							left: 0,
							right: 0,
							height: "60%",
							background: gradients.cardSubtle,
							pointerEvents: "none",
						}}
					/>

					{/* Type badge — label + color come from the adapter;
					    card does not branch on listing.type directly. */}
					<Box
						style={{
							position: "absolute",
							top: 10,
							left: 10,
							display: "flex",
							gap: 4,
							alignItems: "center",
						}}
					>
						<Box
							style={{
								backgroundColor: cardContent.dealTypeBadge.bg,
								backdropFilter: "blur(8px)",
								borderRadius: radii.sm,
								padding: "3px 8px",
							}}
						>
							<Text size="10px" fw={700} c="white" lh={1.3}>
								{t(cardContent.dealTypeBadge.labelKey)}
							</Text>
						</Box>
						{/* Status badges (verified, urgent, …) — pure render of
						    the adapter-supplied array. The card adds no logic
						    of its own. To add a new badge kind, extend the
						    adapter; the UI requires no change. */}
						{cardContent.badges.map((badge) => (
							<Box
								key={badge.type}
								style={{
									backgroundColor: BADGE_BG[badge.type],
									backdropFilter: "blur(8px)",
									borderRadius: radii.sm,
									padding: "3px 8px",
								}}
							>
								<Text size="10px" fw={700} c="white" lh={1.3}>
									{badge.label}
								</Text>
							</Box>
						))}
					</Box>

					{/* Favorite */}
					{onFavorite && (
						<ActionIcon
							variant="transparent"
							size={36}
							style={{ position: "absolute", top: 8, right: 8, zIndex: 2 }}
							onClick={(e) => {
								e.stopPropagation();
								onFavorite(listing.id);
							}}
						>
							<IconHeart
								size={24}
								fill={isFavorited ? "#ff6b6b" : "none"}
								color={isFavorited ? "#ff6b6b" : "white"}
								style={{ filter: "drop-shadow(0 1px 3px rgba(0,0,0,0.4))" }}
							/>
						</ActionIcon>
					)}

					{/* Price — suffix ("/ мес", "/ сутки") is now baked into
					    formatPrice via the adapter-chosen period, so the card
					    doesn't decide rent vs. sale here. */}
					<Box
						style={{
							position: "absolute",
							bottom: 10,
							left: 10,
							backgroundColor: "rgba(255,255,255,0.95)",
							backdropFilter: "blur(8px)",
							borderRadius: radii.md,
							padding: "3px 8px",
							boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
						}}
					>
						<Text size="xs" fw={800} c="dark.8" lh={1.3}>
							{formattedPrice}
						</Text>
					</Box>
				</Box>

				{/* Info — all text truncates, never overflows */}
				<Box
					style={{
						padding: spacing.cardCompact,
						minWidth: 0,
						...(layout === "grid" ? { height: 104, overflow: "hidden" } : {}),
					}}
				>
					<Text
						size="xs"
						fw={600}
						c="dark.7"
						mb={2}
						truncate
						style={{ fontFamily: "var(--mantine-font-family-headings)" }}
					>
						{propertyLabel}
						{titleSuffix && (
							<Text span c="gray.6" fw={500}>
								{titleSuffix}
							</Text>
						)}
					</Text>

					<Box
						style={{
							display: "flex",
							alignItems: "center",
							gap: 4,
							marginBottom: 6,
							minWidth: 0,
							overflow: "hidden",
						}}
					>
						<IconMapPin
							size={13}
							color="var(--mantine-color-gray-5)"
							stroke={2}
							style={{ flexShrink: 0 }}
						/>
						<Text size="xs" c="gray.6" fw={500} truncate>
							{fullLocationLabel}
						</Text>
					</Box>

					{/* Info chips — area, rooms, floor */}
					{/* Info chips — iterate over adapter-derived list. Card
					    does not decide which chips to show; the visibility
					    matrix does (via getCardChipFields inside the adapter). */}
					<Box
						style={{
							display: "flex",
							gap: 6,
							alignItems: "center",
							minWidth: 0,
							minHeight: 16,
						}}
					>
						{cardContent.chips.map((chip) => {
							const Icon = CHIP_ICON[chip.key] ?? IconRuler;
							return (
								<Box
									key={chip.key}
									style={{
										display: "flex",
										alignItems: "center",
										gap: 3,
										flexShrink: 0,
									}}
								>
									<Icon
										size={13}
										color="var(--mantine-color-gray-5)"
										stroke={2}
									/>
									<Text size="xs" c="gray.6" fw={500}>
										{chip.label}
									</Text>
								</Box>
							);
						})}
					</Box>

					{/* Tag line (building_type / condition / land_purpose) —
					    also adapter-derived. No placeholder: if the line is
					    empty we render nothing (spec: "No placeholders like -
					    or N/A"). */}
					{tagLine && (
						<Text size="xs" c="blue.5" fw={500} mt={4} truncate>
							{tagLine}
						</Text>
					)}
				</Box>
			</Box>
		</UnstyledButton>
	);
};
