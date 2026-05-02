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
import { CommentsDrawer } from "./CommentsDrawer";
import { radii } from "@app/styles/theme";

interface DescriptionDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	onCommentAdded?: () => void;
}

export const DescriptionDrawer: FC<DescriptionDrawerProps> = ({
	opened,
	onClose,
	listing,
	onCommentAdded,
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

	const rawText = listing.raw_text || listing.description;
	const fullText = rawText
		?.replace(/##\s*Фото\s*\/\s*Images\s*/gi, "")
		.replace(/-\s*Image\s*\d+:\s*https?:\/\/\S+/g, "")
		.replace(/https?:\/\/\S*apollo\.olxcdn\.com\S*/g, "")
		.replace(/\*{0,2}Продавец:\*{0,2}[\s\S]*$/i, "")
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
				styles={{
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
