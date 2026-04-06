import { ReactNode } from "react";
import { Box, Group, Text } from "@mantine/core";
import { IconDoor } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { ListingImageThumbnail } from "./ListingImageThumbnail";
import { formatPrice, radii, shadows, spacing, surface } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";

interface ListingRowProps {
	/** Image URL */
	imageUrl?: string | null;
	/** Price */
	price: number;
	/** Currency */
	currency?: string;
	/** Is rent (show /month suffix) */
	isRent?: boolean;
	/** Description or title — 1 line truncated */
	description?: string | null;
	/** Number of rooms */
	rooms?: number | null;
	/** Area in sqm */
	area?: number | null;
	/** District key (will be translated) */
	district?: string | null;
	/** Date string to display */
	date?: string | null;
	/** Click handler */
	onClick?: () => void;
	/** Extra elements rendered in the top-right corner (badges, menu, actions) */
	actions?: ReactNode;
	/** Extra content rendered below the info block */
	children?: ReactNode;
}

/**
 * Universal listing row card used across Favorites, My Listings, and Crawled.
 * Thumbnail left, info right. Pass `actions` for top-right badges/menus,
 * `children` for additional content below.
 */
export function ListingRow({
	imageUrl,
	price,
	currency,
	isRent,
	description,
	rooms,
	area,
	district,
	date,
	onClick,
	actions,
	children,
}: ListingRowProps) {
	const { t } = useTranslation("buyer");

	const districtLabel = district ? translateDistrict(district, t) : null;

	const infoParts: string[] = [];
	if (rooms) infoParts.push(`${rooms} ${t("common.rooms")}`);
	if (area) infoParts.push(`${area} ${t("common.sqm")}`);
	if (districtLabel) infoParts.push(districtLabel);

	return (
		<Box
			onClick={onClick}
			style={{
				backgroundColor: surface.card,
				borderRadius: radii.lg,
				padding: spacing.cardCompact,
				boxShadow: shadows.md,
				cursor: onClick ? "pointer" : "default",
				transition: "all 0.15s ease",
			}}
		>
			<Group wrap="nowrap" gap="md">
				<ListingImageThumbnail src={imageUrl ?? null} />
				<Box style={{ flex: 1, minWidth: 0 }}>
					{/* Price + actions */}
					<Group justify="space-between" wrap="nowrap" mb={2}>
						<Text size="lg" fw={700} truncate>
							{formatPrice(price, currency)}
							{isRent && (
								<Text span size="xs" fw={500} c="dimmed">
									{t("common.perMonth")}
								</Text>
							)}
						</Text>
						{actions}
					</Group>

					{/* Description */}
					{description && (
						<Text size="sm" c="dimmed" lineClamp={1}>
							{description}
						</Text>
					)}

					{/* Info chips: rooms · area · district */}
					{infoParts.length > 0 && (
						<Group gap={4} wrap="nowrap" mt={2}>
							{rooms && (
								<IconDoor
									size={12}
									color="var(--mantine-color-gray-5)"
								/>
							)}
							<Text size="xs" c="dimmed" truncate>
								{infoParts.join(" · ")}
							</Text>
						</Group>
					)}

					{/* Date */}
					{date && (
						<Text size="xs" c="dimmed" mt={4}>
							{date}
						</Text>
					)}

					{/* Extra content */}
					{children}
				</Box>
			</Group>
		</Box>
	);
}
