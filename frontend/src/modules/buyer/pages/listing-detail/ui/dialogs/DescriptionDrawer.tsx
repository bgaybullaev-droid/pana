import { FC, useState, useRef } from "react";
import {
	Drawer,
	Box,
	Text,
	Stack,
	Group,
	Badge,
	ScrollArea,
} from "@mantine/core";
import { IconMapPin, IconPhone } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict } from "@shared/lib/regions";
import { useSwipeDismiss } from "@shared/hooks/useSwipeDismiss";
import { formatPhone } from "@shared/lib/formatPhone";
import { trackContact } from "@shared/lib/viewTracking";
import { CommentsDrawer } from "./CommentsDrawer";
import { radii } from "@app/styles/theme";

interface DescriptionDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	onCommentAdded?: () => void;
	/**
	 * When set, the drawer is rendered *inside* this element (via portal)
	 * with absolute positioning instead of covering the whole viewport.
	 * Used by the seller Stage-2 preview so the drawer stays within the
	 * "phone screenshot" frame. The container must be `position: relative`.
	 */
	container?: HTMLElement | null;
}

export const DescriptionDrawer: FC<DescriptionDrawerProps> = ({
	opened,
	onClose,
	listing,
	onCommentAdded,
	container,
}) => {
	const { t } = useTranslation("buyer");
	const [commentsOpen, setCommentsOpen] = useState(false);
	const scrollRef = useRef<HTMLDivElement>(null);

	const { dragOffset, isDragging, isClosing, handlers } = useSwipeDismiss({
		onClose,
		threshold: 120,
		resistance: 0.6,
		scrollRef,
		enabled: opened,
	});

	// Block A6 — locale-driven section markers. The raw_text shipped by the
	// crawler embeds source-language section headers (currently always Russian
	// for OLX, but we route through i18n so future per-locale crawlers can
	// override). Each key resolves to a regex *source* string; we build the
	// RegExp here.
	const rawText = listing.raw_text || listing.description;
	const photoHeaderRe = new RegExp(
		t("descriptionDrawer.section.photoHeaderRe"),
		"gi",
	);
	const imageLineRe = new RegExp(t("descriptionDrawer.section.imageLineRe"), "g");
	const imageHostRe = new RegExp(t("descriptionDrawer.section.imageHostRe"), "g");
	const sellerTrailerRe = new RegExp(
		t("descriptionDrawer.section.sellerTrailerRe"),
		"i",
	);
	const fullText = rawText
		?.replace(photoHeaderRe, "")
		.replace(imageLineRe, "")
		.replace(imageHostRe, "")
		.replace(sellerTrailerRe, "")
		.replace(/\n{3,}/g, "\n\n")
		.trim();

	// Transition: none during drag, spring on snap-back, ease-out on close
	const transition = isDragging
		? "none"
		: isClosing
			? "transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
			: "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";

	return (
		<>
			<Drawer
				opened={opened}
				onClose={onClose}
				position="bottom"
				size="80%"
				withCloseButton={false}
				lockScroll={!container}
				portalProps={container ? { target: container } : undefined}
				styles={{
					// When contained in the preview frame, switch the overlay
					// + positioning layer from `fixed` (viewport) to `absolute`
					// (the relative-positioned preview container).
					...(container
						? {
								root: { position: "absolute", inset: 0 },
								overlay: { position: "absolute" },
								inner: { position: "absolute" },
							}
						: {}),
					content: {
						borderTopLeftRadius: radii.lg,
						borderTopRightRadius: radii.lg,
						overflow: "hidden",
					},
					body: {
						padding: 0,
						height: "100%",
						display: "flex",
						flexDirection: "column",
					},
				}}
			>
				<Box
					{...handlers}
					style={{
						display: "flex",
						flexDirection: "column",
						height: "100%",
						transform: `translateY(${dragOffset}px)`,
						transition,
					}}
				>
					{/* Drag handle */}
					<Box
						py={10}
						style={{
							display: "flex",
							justifyContent: "center",
							cursor: "grab",
							flexShrink: 0,
						}}
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

					{/* Header — title only, no close button */}
					<Box
						px="md"
						pb="sm"
						style={{
							borderBottom: "1px solid var(--mantine-color-gray-2)",
							flexShrink: 0,
						}}
					>
						<Text fw={600} size="lg">
							{t("description.title")}
						</Text>
					</Box>

					{/* Content */}
					<ScrollArea
						style={{ flex: 1 }}
						px="md"
						py="sm"
						viewportRef={scrollRef}
					>
						<Stack gap="md">
							{listing.title && (
								<Text fw={600} size="md">
									{listing.title}
								</Text>
							)}

							<Group gap={6}>
								<Badge
									size="sm"
									variant="light"
									color={listing.type === "sell" ? "blue" : "green"}
								>
									{listing.type === "sell"
										? t("listing.typeSell")
										: t("listing.typeRent")}
								</Badge>
								{listing.rooms && (
									<Badge size="sm" variant="outline" color="gray">
										{listing.rooms} {t("listing.rooms")}
									</Badge>
								)}
								{listing.area && (
									<Badge size="sm" variant="outline" color="gray">
										{listing.area} {t("listing.area")}
									</Badge>
								)}
								{listing.floor && (
									<Badge size="sm" variant="outline" color="gray">
										{listing.floor}/{listing.total_floors || "?"}{" "}
										{t("listing.floorLabel")}
									</Badge>
								)}
							</Group>

							{fullText && (
								<Text
									size="sm"
									style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}
								>
									{fullText}
								</Text>
							)}

							{(listing.district || listing.address) && (
								<Group gap="xs" align="flex-start">
									<IconMapPin
										size={16}
										color="var(--mantine-color-gray-6)"
										style={{ marginTop: 2, flexShrink: 0 }}
									/>
									<Text size="sm" c="dimmed">
										{[translateDistrict(listing.district, t), listing.address]
											.filter(Boolean)
											.join(", ")}
									</Text>
								</Group>
							)}

							{listing.contact_phone && (
								<Group gap="xs">
									<IconPhone size={16} color="var(--mantine-color-gray-6)" />
									<Text
										size="sm"
										c="blue"
										fw={500}
										component="a"
										href={`tel:${listing.contact_phone}`}
										onClick={() => {
											void trackContact(listing.id);
										}}
									>
										{formatPhone(listing.contact_phone)}
									</Text>
								</Group>
							)}
						</Stack>
					</ScrollArea>
				</Box>
			</Drawer>

			<CommentsDrawer
				opened={commentsOpen}
				onClose={() => setCommentsOpen(false)}
				listingId={listing.id}
				onCommentAdded={onCommentAdded}
			/>
		</>
	);
};
