import { FC, Suspense, lazy } from "react";
import { Drawer, Box, Text, Group, UnstyledButton } from "@mantine/core";
import { IconMapPin, IconArrowLeft } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict } from "@shared/lib/regions";
import { getListingCoords } from "../main/ListingMap";
import { radii } from "@app/styles/theme";
import { DrawerBackButton } from "./DrawerBackButton";
import { useTelegramBackClose } from "@shared/hooks/useTelegramBackClose";

const ListingMap = lazy(() =>
	import("../main/ListingMap").then((m) => ({ default: m.ListingMap })),
);

interface MapDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	/** Close the map and open the description drawer instead. */
	onBackToDescription?: () => void;
	/** See DescriptionDrawer.container — contains the drawer within the
	 *  seller Stage-2 preview frame instead of the full viewport. */
	container?: HTMLElement | null;
}

export const MapDrawer: FC<MapDrawerProps> = ({
	opened,
	onClose,
	listing,
	onBackToDescription,
	container,
}) => {
	// Telegram Back closes this overlay instead of navigating
	useTelegramBackClose(opened, onClose);
	const { t } = useTranslation("buyer");
	const coords = getListingCoords(listing);
	const locationText = [translateDistrict(listing.district, t), listing.address]
		.filter(Boolean)
		.join(", ");

	return (
		<Drawer
			opened={opened}
			onClose={onClose}
			position="bottom"
			size="90%"
			withCloseButton={false}
			lockScroll={!container}
			zIndex={10001}
			portalProps={container ? { target: container } : undefined}
			styles={{
				...(container
					? {
							root: { position: "absolute", inset: 0 },
							overlay: { position: "absolute" },
							inner: { position: "absolute" },
						}
					: {}),
				content: { borderTopLeftRadius: radii.lg, borderTopRightRadius: radii.lg },
				body: {
					padding: 0,
					height: "100%",
					display: "flex",
					flexDirection: "column",
					position: "relative",
				},
			}}
		>
			{/* Drag handle */}
			<Box
				py={8}
				style={{
					display: "flex",
					justifyContent: "center",
					cursor: "grab",
					flexShrink: 0,
				}}
				onClick={onClose}
			>
				<Box
					style={{
						width: 36,
						height: 4,
						borderRadius: 2,
						backgroundColor: "var(--mantine-color-gray-4)",
					}}
				/>
			</Box>

			{/* Map — on top, fills the remaining space */}
			<Box style={{ flex: 1, minHeight: 0, padding: 12 }}>
				{coords ? (
					<Suspense
						fallback={<Box h="100%" bg="gray.1" style={{ borderRadius: radii.md }} />}
					>
						<ListingMap
							lat={coords.lat}
							lng={coords.lng}
							exact={coords.exact}
							height="100%"
						/>
					</Suspense>
				) : (
					<Box
						h="100%"
						bg="gray.1"
						style={{
							borderRadius: radii.md,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<Text c="dimmed" size="sm">
							Location not available
						</Text>
					</Box>
				)}
			</Box>

			{/* Address — below the map; right padding clears the round buttons */}
			<Box px="md" pt="sm" pb={72} style={{ flexShrink: 0 }}>
				<Group gap={6} align="flex-start" wrap="nowrap" style={{ paddingRight: 64 }}>
					<IconMapPin
						size={18}
						color="var(--mantine-color-blue-6)"
						style={{ flexShrink: 0, marginTop: 2 }}
					/>
					<Text fw={500} size="sm">
						{locationText || t("home.region")}
					</Text>
				</Group>
				{onBackToDescription && (
					<UnstyledButton
						onClick={onBackToDescription}
						mt={8}
						style={{
							display: "inline-flex",
							alignItems: "center",
							gap: 6,
							color: "var(--mantine-color-blue-6)",
							fontSize: "var(--mantine-font-size-sm)",
						}}
					>
						<IconArrowLeft size={14} />
						{t("descriptionDrawer.backToDescription", "К описанию")}
					</UnstyledButton>
				)}
			</Box>

			{/* Back — pinned outside the sliding sheet so it stays put (no slide-up). */}
			<DrawerBackButton opened={opened} onClose={onClose} container={container} />
		</Drawer>
	);
};
