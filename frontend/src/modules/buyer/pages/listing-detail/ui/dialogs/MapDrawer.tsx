import { FC, Suspense, lazy } from "react";
import { Drawer, Box, Text, Group, UnstyledButton } from "@mantine/core";
import { IconMapPin, IconArrowLeft } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict } from "@shared/lib/regions";
import { getListingCoords } from "../main/ListingMap";
import { radii, shadows } from "@app/styles/theme";

const ListingMap = lazy(() =>
	import("../main/ListingMap").then((m) => ({ default: m.ListingMap })),
);

interface MapDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	/** See DescriptionDrawer.container — contains the drawer within the
	 *  seller Stage-2 preview frame instead of the full viewport. */
	container?: HTMLElement | null;
}

export const MapDrawer: FC<MapDrawerProps> = ({
	opened,
	onClose,
	listing,
	container,
}) => {
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
							height={400}
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
			</Box>

			{/* Close — same dark round button as the listing back; closes the map */}
			<UnstyledButton
				onClick={onClose}
				aria-label={t("descriptionDrawer.back", "Назад")}
				style={{
					position: "absolute",
					right: 12,
					bottom: "max(12px, env(safe-area-inset-bottom, 12px))",
					width: 45,
					height: 45,
					borderRadius: "50%",
					backgroundColor: "rgba(0, 0, 0, 0.6)",
					backdropFilter: "blur(20px) saturate(180%)",
					WebkitBackdropFilter: "blur(20px) saturate(180%)",
					border: "1px solid rgba(255, 255, 255, 0.25)",
					boxShadow: shadows.md,
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
				}}
			>
				<IconArrowLeft size={24} stroke={1.8} color="#fff" />
			</UnstyledButton>
		</Drawer>
	);
};
