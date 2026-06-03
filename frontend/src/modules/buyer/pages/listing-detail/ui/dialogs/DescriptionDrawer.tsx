import { FC, useState, useRef } from "react";
import {
	Drawer,
	Box,
	Text,
	Stack,
	Group,
	Badge,
	ScrollArea,
	Avatar,
	Button,
	SimpleGrid,
	ThemeIcon,
	Divider,
} from "@mantine/core";
import {
	IconMapPin,
	IconPhone,
	IconUser,
	IconHome,
	IconBed,
	IconRuler2,
	IconStairs,
	IconShieldCheck,
	IconCalendar,
	IconEye,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict } from "@shared/lib/regions";
import { useSwipeDismiss } from "@shared/hooks/useSwipeDismiss";
import { formatPhone } from "@shared/lib/formatPhone";
import { trackContact } from "@shared/lib/viewTracking";
import { CommentsDrawer } from "./CommentsDrawer";
import { formatPrice, radii } from "@app/styles/theme";

interface DescriptionDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	onCommentAdded?: () => void;
}

type ParamRow = { icon: typeof IconHome; value: string | number; label: string };

// Apartment/house amenity codes → seller-namespace i18n keys. Reused so we
// don't duplicate ~20 labels across four locale files; unknown codes fall
// back to the raw value.
const AMENITY_I18N: Record<string, string> = {
	internet: "createListing.amenInternet",
	phone: "createListing.amenPhone",
	fridge: "createListing.amenFridge",
	tv: "createListing.amenTv",
	ac: "createListing.amenAc",
	cable_tv: "createListing.amenCable",
	washing_machine: "createListing.amenWashing",
	kitchen_set: "createListing.amenKitchen",
	balcony: "createListing.amenBalcony",
	pool: "createListing.amenPool",
	garage: "createListing.amenGarage",
	appliances: "createListing.amenAppliances",
	sewage: "createListing.amenSewage",
	garden: "createListing.amenGarden",
	security: "createListing.amenSecurity",
	basement: "createListing.amenBasement",
	sauna: "createListing.amenSauna",
	gym: "createListing.amenGym",
	satellite_tv: "createListing.amenSatellite",
};

export const DescriptionDrawer: FC<DescriptionDrawerProps> = ({
	opened,
	onClose,
	listing,
	onCommentAdded,
}) => {
	const { t, i18n } = useTranslation("buyer");
	const navigate = useNavigate();
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
	// RegExp here. The params/price/header markers strip the structured dump
	// that we now render as its own blocks, leaving only the human-written body.
	const rawText = listing.raw_text || listing.description;
	const photoHeaderRe = new RegExp(
		t("descriptionDrawer.section.photoHeaderRe"),
		"gi",
	);
	const imageLineRe = new RegExp(t("descriptionDrawer.section.imageLineRe"), "g");
	const imageHostRe = new RegExp(t("descriptionDrawer.section.imageHostRe"), "g");
	const paramsBlockRe = new RegExp(
		t("descriptionDrawer.section.paramsBlockRe"),
		"gi",
	);
	const priceLineRe = new RegExp(t("descriptionDrawer.section.priceLineRe"), "gi");
	const descriptionHeaderRe = new RegExp(
		t("descriptionDrawer.section.descriptionHeaderRe"),
		"gi",
	);
	const sellerTrailerRe = new RegExp(
		t("descriptionDrawer.section.sellerTrailerRe"),
		"i",
	);
	const fullText = rawText
		?.replace(photoHeaderRe, "")
		.replace(imageLineRe, "")
		.replace(imageHostRe, "")
		.replace(paramsBlockRe, "")
		.replace(priceLineRe, "")
		.replace(descriptionHeaderRe, "")
		.replace(sellerTrailerRe, "")
		.replace(/\n{3,}/g, "\n\n")
		.trim();

	// Transition: none during drag, spring on snap-back, ease-out on close
	const transition = isDragging
		? "none"
		: isClosing
			? "transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
			: "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";

	const formattedPrice = formatPrice(listing.price, listing.currency);
	const dealLabel =
		listing.type === "sell" ? t("listing.typeSell") : t("listing.typeRent");
	const propertyLabel = t(
		`card.propertyType.${listing.property_type}`,
		listing.property_type,
	);

	// Key parameters grid. Property type carries the deal type as its label so we
	// reuse existing i18n keys instead of inventing per-param captions.
	const params: ParamRow[] = [
		{ icon: IconHome, value: propertyLabel, label: dealLabel },
	];
	if (listing.rooms)
		params.push({
			icon: IconBed,
			value: listing.rooms,
			label: t("listing.rooms"),
		});
	if (listing.area)
		params.push({
			icon: IconRuler2,
			value: listing.area,
			label: t("listing.area"),
		});
	if (listing.floor)
		params.push({
			icon: IconStairs,
			value: `${listing.floor}/${listing.total_floors || "?"}`,
			label: t("listing.floorLabel"),
		});

	// Characteristics — building type / condition as subtle tags (translated
	// with fallback to the raw value for unknown crawler enums).
	const attributes: string[] = [];
	if (listing.building_type)
		attributes.push(
			t(`listing.buildingType.${listing.building_type}`, listing.building_type),
		);
	if (listing.condition)
		attributes.push(t(`listing.condition.${listing.condition}`, listing.condition));

	const amenities = listing.amenities ?? [];
	const amenityLabel = (a: string) => {
		const key = AMENITY_I18N[a];
		return key ? t(key, { ns: "seller", defaultValue: a }) : a;
	};
	const hasSeller = Boolean(
		listing.seller_id && (listing.seller_name || listing.seller_avatar_url),
	);
	const publishedAt = new Date(listing.created_at).toLocaleDateString(
		i18n.language?.startsWith("uz") ? "uz-Latn" : "ru-RU",
		{ day: "numeric", month: "long", year: "numeric" },
	);

	return (
		<>
			<Drawer
				opened={opened}
				onClose={onClose}
				position="bottom"
				size="85%"
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

					{/* Content */}
					<ScrollArea style={{ flex: 1 }} px="md" py="sm" viewportRef={scrollRef}>
						<Stack gap="md">
							{/* Price hero + deal type */}
							<Group justify="space-between" align="flex-start" wrap="nowrap">
								<Text fw={800} style={{ fontSize: 26, lineHeight: 1.1 }}>
									{formattedPrice}
								</Text>
								<Badge
									size="lg"
									variant="light"
									radius="sm"
									color={listing.type === "sell" ? "blue" : "green"}
								>
									{dealLabel}
								</Badge>
							</Group>

							{listing.title && (
								<Text fw={600} size="md">
									{listing.title}
								</Text>
							)}

							{/* Key parameters */}
							<SimpleGrid cols={2} spacing="sm" verticalSpacing="sm">
								{params.map((p, idx) => {
									const ItemIcon = p.icon;
									return (
										<Group key={idx} gap={10} wrap="nowrap">
											<ThemeIcon
												variant="light"
												color="blue"
												size={38}
												radius="md"
											>
												<ItemIcon size={20} />
											</ThemeIcon>
											<Box style={{ minWidth: 0 }}>
												<Text fw={700} size="sm" lh={1.2} truncate>
													{p.value}
												</Text>
												<Text size="xs" c="dimmed" lh={1.2} truncate>
													{p.label}
												</Text>
											</Box>
										</Group>
									);
								})}
							</SimpleGrid>

							{/* Characteristics */}
							{attributes.length > 0 && (
								<Group gap={6}>
									{attributes.map((a) => (
										<Badge
											key={a}
											size="sm"
											variant="light"
											color="gray"
											radius="sm"
										>
											{a}
										</Badge>
									))}
								</Group>
							)}

							{/* Amenities */}
							{amenities.length > 0 && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.amenities")}
									</Text>
									<Group gap={6}>
										{amenities.map((a) => (
											<Badge
												key={a}
												size="sm"
												variant="outline"
												color="gray"
												radius="sm"
											>
												{amenityLabel(a)}
											</Badge>
										))}
									</Group>
								</Stack>
							)}

							{/* Description */}
							{fullText && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("description.title")}
									</Text>
									<Text
										size="sm"
										style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}
									>
										{fullText}
									</Text>
								</Stack>
							)}

							{/* Location */}
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

							{/* Seller */}
							{hasSeller && (
								<>
									<Divider />
									<Group
										gap={10}
										wrap="nowrap"
										style={{ cursor: "pointer" }}
										onClick={() => navigate(`/seller/${listing.seller_id}`)}
									>
										<Avatar
											src={listing.seller_avatar_url}
											size={42}
											radius={21}
											color="gray.5"
										>
											<IconUser size={22} />
										</Avatar>
										<Box style={{ minWidth: 0 }}>
											<Group gap={4} wrap="nowrap">
												<Text fw={600} size="sm" truncate>
													{listing.seller_name || t("descriptionDrawer.seller")}
												</Text>
												{listing.seller_verified && (
													<IconShieldCheck
														size={16}
														color="var(--mantine-color-blue-6)"
														style={{ flexShrink: 0 }}
													/>
												)}
											</Group>
											<Text size="xs" c="dimmed">
												{t("descriptionDrawer.seller")}
											</Text>
										</Box>
									</Group>
								</>
							)}

							{/* Meta */}
							<Group gap="md" pt={2}>
								<Group gap={4} wrap="nowrap">
									<IconCalendar size={14} color="var(--mantine-color-gray-5)" />
									<Text size="xs" c="dimmed">
										{publishedAt}
									</Text>
								</Group>
								<Group gap={4} wrap="nowrap">
									<IconEye size={14} color="var(--mantine-color-gray-5)" />
									<Text size="xs" c="dimmed">
										{listing.views_count}
									</Text>
								</Group>
							</Group>
						</Stack>
					</ScrollArea>

					{/* Sticky call CTA */}
					{listing.contact_phone && (
						<Box
							px="md"
							py="sm"
							style={{
								borderTop: "1px solid var(--mantine-color-gray-2)",
								flexShrink: 0,
							}}
						>
							<Button
								fullWidth
								size="md"
								radius="md"
								leftSection={<IconPhone size={18} />}
								component="a"
								href={`tel:${listing.contact_phone}`}
								onClick={() => {
									void trackContact(listing.id);
								}}
							>
								{t("descriptionDrawer.call")} ·{" "}
								{formatPhone(listing.contact_phone)}
							</Button>
						</Box>
					)}
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
