import { FC, Suspense, lazy } from "react";
import { Drawer, Box, Text, Group, ActionIcon } from "@mantine/core";
import { IconX, IconMapPin } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict } from "@shared/lib/regions";
import { getListingCoords } from "../main/ListingMap";
import { radii } from "@app/styles/theme";

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
			size="70%"
			withCloseButton={false}
			lockScroll={!container}
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
				},
			}}
		>
			{/* Drag handle */}
			<Box
				py={8}
				style={{ display: "flex", justifyContent: "center", cursor: "grab" }}
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

			{/* Header */}
			<Box
				px="md"
				pb="sm"
				style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}
			>
				<Group justify="space-between" align="center">
					<Group gap={6}>
						<IconMapPin size={18} color="var(--mantine-color-blue-6)" />
						<Text fw={600} size="lg">
							{locationText || t("home.region")}
						</Text>
					</Group>
					<ActionIcon variant="subtle" onClick={onClose}>
						<IconX size={20} />
					</ActionIcon>
				</Group>
			</Box>

			{/* Map */}
			<Box style={{ flex: 1, padding: 12 }}>
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
		</Drawer>
	);
};
