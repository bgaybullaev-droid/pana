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
import { formatPrice, gradients, radii, shadows, spacing, surface } from "@app/styles/theme";
import { translateDistrict, translateRegion, getRegionForDistrict } from "@shared/lib/regions";

interface ListingCardProps {
	listing: ListingListItem;
	onClick: (id: string) => void;
	isFavorited?: boolean;
	onFavorite?: (id: string) => void;
	layout?: "grid" | "masonry";
}

export const ListingCard: FC<ListingCardProps> = ({
	listing,
	onClick,
	isFavorited,
	onFavorite,
	layout = "grid",
}) => {
	const { t } = useTranslation("buyer");
	const [imageLoaded, setImageLoaded] = useState(false);
	const formattedPrice = formatPrice(listing.price, listing.currency);

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
	
	const fullLocationLabel = locationParts.length > 0 
		? locationParts.join(", ") 
		: t("listing.defaultDistrict");

	// Building type + condition text (e.g. "Новостройка, Евроремонт")
	// Only show translated values — skip unknown raw values from crawlers
	const KNOWN_BUILDING_TYPES = ["new", "secondary"];
	const KNOWN_CONDITIONS = ["euro", "cosmetic", "needs_repair", "rough"];
	const KNOWN_LAND_PURPOSES = ["private", "industrial"];

	let buildingTypeStr = null;
	if (
		listing.building_type &&
		KNOWN_BUILDING_TYPES.includes(listing.building_type)
	) {
		buildingTypeStr = t(`listing.buildingType.${listing.building_type}`);
	}

	const titleSuffix = listing.property_type === "apartment" && buildingTypeStr
		? `, ${buildingTypeStr.toLowerCase()}`
		: "";

	const standardTitle = `${propertyLabel}${titleSuffix}, ${fullLocationLabel}`;

	const tagParts: string[] = [];
	if (
		listing.property_type !== "land" &&
		listing.condition &&
		KNOWN_CONDITIONS.includes(listing.condition)
	) {
		tagParts.push(t(`listing.condition.${listing.condition}`));
	}
	if (
		listing.land_purpose &&
		listing.property_type === "land" &&
		KNOWN_LAND_PURPOSES.includes(listing.land_purpose)
	) {
		tagParts.push(t(`listing.landPurpose.${listing.land_purpose}`));
	}
	const tagLine = tagParts.join(", ");

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

					{/* Type badge */}
					<Box
						style={{
							position: "absolute",
							top: 10,
							left: 10,
							backgroundColor:
								listing.type === "sell"
									? "rgba(34,139,230,0.9)"
									: "rgba(64,192,87,0.9)",
							backdropFilter: "blur(8px)",
							borderRadius: radii.sm,
							padding: "3px 8px",
						}}
					>
						<Text size="10px" fw={700} c="white" lh={1.3}>
							{listing.type === "sell" ? t("common.sell") : t("common.rent")}
						</Text>
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

					{/* Price */}
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
							{listing.type === "rent" && (
								<Text span size="9px" fw={500} c="dimmed">
									{t("common.perMonth")}
								</Text>
							)}
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
					<Box
						style={{
							display: "flex",
							gap: 6,
							alignItems: "center",
							minWidth: 0,
							minHeight: 16,
						}}
					>
						{listing.area != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 3,
									flexShrink: 0,
								}}
							>
								<IconRuler
									size={13}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="xs" c="gray.6" fw={500}>
									{listing.area} {t("common.sqm")}
								</Text>
							</Box>
						)}
						{listing.rooms != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 3,
									flexShrink: 0,
								}}
							>
								<IconBed
									size={13}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="xs" c="gray.6" fw={500}>
									{listing.rooms} {t("common.rooms")}
								</Text>
							</Box>
						)}
						{listing.floor != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 3,
									flexShrink: 0,
								}}
							>
								<IconBuilding
									size={13}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="xs" c="gray.6" fw={500}>
									{listing.floor}/{listing.total_floors || "?"}
								</Text>
							</Box>
						)}
					</Box>

					{/* Building type + condition — always rendered to keep card height uniform */}
					<Text
						size="xs"
						c="blue.5"
						fw={500}
						mt={4}
						truncate
						style={{ visibility: tagLine ? "visible" : "hidden" }}
					>
						{tagLine || "\u00A0"}
					</Text>
				</Box>
			</Box>
		</UnstyledButton>
	);
};
