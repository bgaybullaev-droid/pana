import { FC, useState } from "react";
import { Text, Skeleton, UnstyledButton, Box, ActionIcon } from "@mantine/core";
import {
	IconHeart,
	IconBed,
	IconRuler,
	IconStairs,
	IconMapPin,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { ListingListItem } from "@shared/api/types";
import { formatPrice, gradients } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";

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
		`common.propertyType.${listing.property_type}`,
		listing.property_type,
	);
	const districtLabel =
		translateDistrict(listing.district, t) || t("listing.defaultDistrict");
	const standardTitle = `${propertyLabel}, ${districtLabel}`;

	// Building type + condition text (e.g. "Новостройка, Евроремонт")
	// Only show translated values — skip unknown raw values from crawlers
	const KNOWN_BUILDING_TYPES = ["new", "secondary"];
	const KNOWN_CONDITIONS = ["euro", "cosmetic", "needs_repair", "rough"];
	const KNOWN_LAND_PURPOSES = ["private", "industrial"];

	const tagParts: string[] = [];
	if (
		listing.building_type &&
		KNOWN_BUILDING_TYPES.includes(listing.building_type)
	) {
		tagParts.push(t(`listing.buildingType.${listing.building_type}`));
	}
	if (listing.condition && KNOWN_CONDITIONS.includes(listing.condition)) {
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
					borderRadius: 16,
					overflow: "hidden",
					backgroundColor: "white",
					boxShadow: "0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
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
							borderRadius: 8,
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
							borderRadius: 10,
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
					py={8}
					px={8}
					style={{
						minWidth: 0,
						...(layout === "grid" ? { height: 82, overflow: "hidden" } : {}),
					}}
				>
					<Text
						size="xs"
						fw={600}
						c="dark.7"
						mb={3}
						truncate
						style={{ fontFamily: "var(--mantine-font-family-headings)" }}
					>
						{standardTitle}
					</Text>

					{/* Info chips — area, rooms, floor */}
					<Box
						style={{
							display: "flex",
							gap: 5,
							alignItems: "center",
							minWidth: 0,
							minHeight: 14,
						}}
					>
						{listing.area != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 2,
									flexShrink: 0,
								}}
							>
								<IconRuler
									size={11}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="9px" c="gray.6" fw={500}>
									{listing.area} {t("common.sqm")}
								</Text>
							</Box>
						)}
						{listing.rooms != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 2,
									flexShrink: 0,
								}}
							>
								<IconBed
									size={11}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="9px" c="gray.6" fw={500}>
									{listing.rooms} {t("common.rooms")}
								</Text>
							</Box>
						)}
						{listing.floor != null && (
							<Box
								style={{
									display: "flex",
									alignItems: "center",
									gap: 2,
									flexShrink: 0,
								}}
							>
								<IconStairs
									size={11}
									color="var(--mantine-color-gray-5)"
									stroke={2}
								/>
								<Text size="9px" c="gray.6" fw={500}>
									{listing.floor}/{listing.total_floors || "?"}
								</Text>
							</Box>
						)}
					</Box>

					{/* District — always rendered to keep card height uniform */}
					<Box
						style={{
							display: "flex",
							alignItems: "center",
							gap: 2,
							marginTop: 3,
							minWidth: 0,
							overflow: "hidden",
							visibility: listing.district ? "visible" : "hidden",
						}}
					>
						<IconMapPin
							size={11}
							color="var(--mantine-color-gray-5)"
							stroke={2}
							style={{ flexShrink: 0 }}
						/>
						<Text size="9px" c="gray.5" fw={500} truncate>
							{listing.district
								? translateDistrict(listing.district, t)
								: "\u00A0"}
						</Text>
					</Box>

					{/* Building type + condition — always rendered to keep card height uniform */}
					<Text
						size="9px"
						c="blue.5"
						fw={500}
						mt={2}
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
