import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Container,
	Stack,
	Text,
	Group,
	Badge,
	Menu,
	ActionIcon,
	Box,
	Modal,
	Skeleton,
	Button,
	TextInput,
	ScrollArea,
	UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconPlus,
	IconDotsVertical,
	IconEdit,
	IconPlayerPause,
	IconPlayerPlay,
	IconTrash,
	IconEye,
	IconPhone,
	IconBuilding,
	IconSearch,
	IconX,
	IconHeart,
	IconArrowRight,
	IconCoin,
	IconBolt,
} from "@tabler/icons-react";
import { BoostModal } from "@modules/seller/feature/promotion-purchase";
import { useTranslation } from "react-i18next";
import { InnerPage } from "@shared/ui/InnerPage";
import {
	$sellerListings,
	$isLoadingListings,
	fetchSellerListings,
	pauseListing,
	activateListing,
	deleteListing,
	pauseListingFx,
	activateListingFx,
	deleteListingFx,
} from "@modules/seller/shared/state";
import {
	seedListingIds,
	seedListingSource,
} from "@modules/buyer/shared/state/model/events";
import { EmptyState } from "@shared/ui/EmptyState";
import { ListingRow } from "@shared/ui/ListingRow";
import { radii, shadows, surface } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";

interface UnifiedCard {
	id: string;
	source: "platform";
	price: number;
	currency: string;
	title: string;
	imageUrl: string | null;
	rooms: number | null;
	area: number | null;
	district: string | null;
	status?: string;
	views_count?: number;
	contacts_count?: number;
	favorites_count?: number;
	property_type: string;
}

const statusColors: Record<string, string> = {
	active: "#40c057",
	paused: "#fab005",
	sold: "#adb5bd",
	expired: "#fa5252",
	pending: "#228be6",
};

function Page() {
	const navigate = useNavigate();
	const { t } = useTranslation("seller");
	const { t: tBuyer } = useTranslation("buyer");
	const [deleteModalOpen, setDeleteModalOpen] = useState(false);
	const [listingToDelete, setListingToDelete] = useState<string | null>(null);
	// Block phase-2 — boost modal state (promotion purchase).
	const [boostModalListingId, setBoostModalListingId] = useState<string | null>(
		null,
	);
	const [listings, isLoading] = useUnit([$sellerListings, $isLoadingListings]);

	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPropertyType, setSelectedPropertyType] = useState<
		string | null
	>(null);
	const [selectedStatus, setSelectedStatus] = useState<string>("active");

	const statusLabels: Record<string, string> = {
		active: t("listings.statusActive"),
		paused: t("listings.statusPaused"),
		sold: t("listings.statusSold"),
		expired: t("listings.statusExpired"),
		pending: t("listings.statusPending"),
	};

	useEffect(() => {
		fetchSellerListings({});
	}, []);

	// Aggregate dashboard counters — Step 7 of EXECUTION_PLAN.
	// Fire-and-forget; the band hides itself if the request fails so
	// listings still render without the totals.
	const [dashboard, setDashboard] = useState<{
		total_listings: number;
		total_views: number;
		total_contacts: number;
		total_favorites: number;
		// Block C V2.0 (C2): live billable + active counts + test-period flag.
		total_billable_listings?: number;
		total_active_listings?: number;
		free_listings_per_seller?: number;
		test_period_active?: boolean;
	} | null>(null);
	useEffect(() => {
		let cancelled = false;
		import("@shared/api/client").then(({ apiClient }) => {
			apiClient
				.get("/sellers/me/dashboard")
				.then((res) => {
					if (!cancelled) setDashboard(res.data);
				})
				.catch(() => {
					/* hide band on failure */
				});
		});
		return () => {
			cancelled = true;
		};
	}, []);

	useEffect(() => {
		const unwatchPause = pauseListingFx.doneData.watch(() => {
			notifications.show({
				title: t("notifications.done"),
				message: t("notifications.paused"),
				color: "yellow",
			});
		});
		const unwatchActivate = activateListingFx.doneData.watch(() => {
			notifications.show({
				title: t("notifications.done"),
				message: t("notifications.activated"),
				color: "green",
			});
		});
		const unwatchDelete = deleteListingFx.doneData.watch(() => {
			notifications.show({
				title: t("notifications.done"),
				message: t("notifications.deleted"),
				color: "green",
			});
			setDeleteModalOpen(false);
			setListingToDelete(null);
		});
		return () => {
			unwatchPause();
			unwatchActivate();
			unwatchDelete();
		};
	}, [t]);

	const propertyTypeLabel = (type: string) => {
		const map: Record<string, string> = {
			apartment: t("propertyTypes.apartment", "Apartments"),
			house: t("propertyTypes.house", "Houses"),
			commercial: t("propertyTypes.commercial", "Commercial"),
			land: t("propertyTypes.land", "Land"),
		};
		return map[type] || type;
	};

	const platformListings = useMemo(() => listings, [listings]);

	const ALL_PROPERTY_TYPES = ["apartment", "house", "commercial", "land"];
	const ALL_STATUSES = ["active", "paused", "pending", "expired", "sold"];

	// Count exactly how many platform listings match each type
	const propertyCounts = useMemo(() => {
		// Only count listings that match the CURRENT selectedStatus
		const relevantListings = platformListings.filter(
			(l) => !selectedStatus || l.status === selectedStatus,
		);
		const counts: Record<string, number> = { all: relevantListings.length };
		ALL_PROPERTY_TYPES.forEach((type) => {
			counts[type] = 0;
		});

		relevantListings.forEach((l) => {
			if (l.property_type && counts[l.property_type] !== undefined) {
				counts[l.property_type]++;
			}
		});
		return counts;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [platformListings, selectedStatus]);

	// Count exactly how many platform listings match each status
	const statusCounts = useMemo(() => {
		// Only count listings that match the CURRENT selectedPropertyType
		const relevantListings = platformListings.filter(
			(l) => !selectedPropertyType || l.property_type === selectedPropertyType,
		);
		const counts: Record<string, number> = { all: relevantListings.length };
		ALL_STATUSES.forEach((s) => {
			counts[s] = 0;
		});

		relevantListings.forEach((l) => {
			if (l.status && counts[l.status] !== undefined) {
				counts[l.status]++;
			}
		});
		return counts;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [platformListings, selectedPropertyType]);

	const unifiedCards = useMemo((): UnifiedCard[] => {
		const cards: UnifiedCard[] = [];

		for (const l of platformListings) {
			// Filter by property type and status
			if (selectedPropertyType && l.property_type !== selectedPropertyType)
				continue;
			if (selectedStatus && l.status !== selectedStatus) continue;

			const generatedTitle =
				l.title ||
				`${l.rooms ? `${l.rooms}-${t("listings.rooms")} ` : ""}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t("listings.inDistrict", { district: translateDistrict(l.district, t) })}` : ""}`;

			// Filter by search query
			if (searchQuery.trim() !== "") {
				const query = searchQuery.toLowerCase();
				const districtName = l.district
					? translateDistrict(l.district, t).toLowerCase()
					: "";

				if (
					!generatedTitle.toLowerCase().includes(query) &&
					!districtName.includes(query)
				) {
					continue;
				}
			}

			cards.push({
				id: l.id,
				source: "platform",
				price: l.price,
				currency: l.currency,
				title: generatedTitle,
				imageUrl: l.primary_image_url,
				rooms: l.rooms,
				area: l.area,
				district: l.district,
				status: l.status,
				views_count: l.views_count,
				contacts_count: l.contacts_count,
				favorites_count: l.favorites_count,
				property_type: l.property_type,
			});
		}

		return cards;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [platformListings, selectedPropertyType, searchQuery, t]);

	const handleDeleteClick = (listingId: string) => {
		setListingToDelete(listingId);
		setDeleteModalOpen(true);
	};

	const confirmDelete = () => {
		if (listingToDelete) deleteListing(listingToDelete);
	};

	return (
		<InnerPage
			title={t("listings.myListings")}
			noPadding
			actions={
				<Group gap={6} wrap="nowrap">
					{dashboard &&
						dashboard.total_active_listings !== undefined &&
						dashboard.free_listings_per_seller !== undefined && (
							<Badge
								variant="light"
								color={dashboard.test_period_active ? "orange" : "blue"}
								radius="sm"
								size="md"
								style={{ cursor: "pointer", fontWeight: 700 }}
								onClick={() => navigate("/seller/tariffs")}
							>
								{dashboard.test_period_active
									? t("myListings.activeChipTest", {
											count: dashboard.total_active_listings,
										})
									: t("myListings.activeChip", {
											count: dashboard.total_active_listings,
											free: dashboard.free_listings_per_seller,
										})}
							</Badge>
						)}
					<ActionIcon
						variant="subtle"
						color="orange"
						radius="xl"
						onClick={() => navigate("/seller/tariffs")}
						aria-label={t("nav.tariffs")}
					>
						<IconCoin size={20} />
					</ActionIcon>
				</Group>
			}
		>
			<Container px="md" py="md">
				<Stack gap={16}>
					{/* Block C V2.0 (C2): test-period banner + active count chip */}
					{dashboard &&
						dashboard.total_billable_listings !== undefined &&
						dashboard.free_listings_per_seller !== undefined && (
							<UnstyledButton
								onClick={() => navigate("/seller/tariffs")}
								style={{ display: "block", width: "100%" }}
								aria-label={t("nav.tariffs")}
							>
								<Box
									p="sm"
									style={{
										background: dashboard.test_period_active
											? "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)"
											: "#dbeafe",
										border: dashboard.test_period_active
											? "1px solid #fcd34d"
											: "1px solid #93c5fd",
										borderRadius: 12,
										cursor: "pointer",
										transition: "transform 0.15s ease",
									}}
								>
									<Group justify="space-between" wrap="nowrap" gap={8}>
										<Box style={{ flex: 1 }}>
											<Text size="sm" fw={600} c="#78350f" lh={1.4}>
												{t("tariffs.banner.myListingsHeader", {
													billable: dashboard.total_billable_listings,
													free: dashboard.free_listings_per_seller,
												})}
											</Text>
											{dashboard.test_period_active && (
												<Text size="xs" c="#92400e" mt={2} lh={1.3}>
													{t("tariffs.banner.myListingsTestPeriod")}
												</Text>
											)}
										</Box>
										<IconArrowRight
											size={18}
											color="#92400e"
											style={{ flexShrink: 0, opacity: 0.7 }}
										/>
									</Group>
								</Box>
							</UnstyledButton>
						)}

					{/* ── Aggregate dashboard band ── */}
					{dashboard && dashboard.total_listings > 0 && (
						<Group
							gap={8}
							grow
							p="sm"
							bg="white"
							style={{
								borderRadius: 12,
								boxShadow: shadows.sm,
								animation: "fade-in 0.3s ease-out",
							}}
						>
							<Stack gap={2} align="center">
								<Group gap={4} wrap="nowrap">
									<IconEye size={14} color="#64748b" />
									<Text size="sm" c="#0f172a" fw={700}>
										{dashboard.total_views}
									</Text>
								</Group>
								<Text size="10px" c="dimmed" tt="uppercase">
									{t("listings.totalViews")}
								</Text>
							</Stack>
							<Stack gap={2} align="center">
								<Group gap={4} wrap="nowrap">
									<IconPhone size={14} color="#64748b" />
									<Text size="sm" c="#0f172a" fw={700}>
										{dashboard.total_contacts}
									</Text>
								</Group>
								<Text size="10px" c="dimmed" tt="uppercase">
									{t("listings.totalContacts")}
								</Text>
							</Stack>
							<Stack gap={2} align="center">
								<Group gap={4} wrap="nowrap">
									<IconHeart size={14} color="#e11d48" />
									<Text size="sm" c="#0f172a" fw={700}>
										{dashboard.total_favorites}
									</Text>
								</Group>
								<Text size="10px" c="dimmed" tt="uppercase">
									{t("listings.totalFavorites")}
								</Text>
							</Stack>
						</Group>
					)}
					{/* ── Search and Filters ── */}
					<Box style={{ animation: "fade-in 0.4s ease-out" }}>
						<TextInput
							placeholder={tBuyer("search.title", "Search")}
							radius="xl"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.currentTarget.value)}
							leftSection={<IconSearch size={20} color="#adb5bd" />}
							rightSection={
								searchQuery ? (
									<ActionIcon
										variant="filled"
										size={18}
										radius="50%"
										color="gray.5"
										onClick={() => setSearchQuery("")}
									>
										<IconX size={10} color="white" />
									</ActionIcon>
								) : null
							}
							styles={{
								input: {
									backgroundColor: "#ffffff",
									border: "1px solid #ced4da",
									boxShadow: shadows.md,
									height: 46,
								},
							}}
						/>

						<ScrollArea
							scrollbarSize={0}
							type="never"
							offsetScrollbars={false}
							mt={12}
						>
							<Box style={{ display: "flex", gap: 8 }}>
								<Box
									onClick={() => setSelectedPropertyType(null)}
									style={{
										padding:
											"5px 15px" /* slightly adjusted to account for border width */,
										borderRadius: radii.full,
										backgroundColor:
											selectedPropertyType === null ? "#228be6" : "#f1f3f5",
										border:
											selectedPropertyType === null
												? "1px solid #228be6"
												: "1px solid #ced4da",
										boxShadow: shadows.md,
										cursor: "pointer",
										whiteSpace: "nowrap",
										transition: "all 0.2s ease",
									}}
								>
									<Text
										size="xs"
										fw={600}
										c={selectedPropertyType === null ? "white" : "gray.7"}
									>
										{t("listings.all", "All")} ({propertyCounts["all"]})
									</Text>
								</Box>
								{ALL_PROPERTY_TYPES.map((type) => {
									const isSelected = selectedPropertyType === type;
									return (
										<Box
											key={type}
											onClick={() => setSelectedPropertyType(type)}
											style={{
												padding: "5px 15px",
												borderRadius: radii.full,
												backgroundColor: isSelected ? "#228be6" : "#f1f3f5",
												border: isSelected
													? "1px solid #228be6"
													: "1px solid #ced4da",
												boxShadow: shadows.md,
												cursor: "pointer",
												whiteSpace: "nowrap",
												transition: "all 0.2s ease",
											}}
										>
											<Text
												size="xs"
												fw={600}
												c={isSelected ? "white" : "gray.7"}
											>
												{propertyTypeLabel(type)} ({propertyCounts[type]})
											</Text>
										</Box>
									);
								})}
							</Box>
						</ScrollArea>

						<ScrollArea
							scrollbarSize={0}
							type="never"
							offsetScrollbars={false}
							mt={8}
						>
							<Box style={{ display: "flex", gap: 8 }}>
								{ALL_STATUSES.map((status) => {
									const isSelected = selectedStatus === status;
									return (
										<Box
											key={status}
											onClick={() => setSelectedStatus(status)}
											style={{
												padding: "5px 15px",
												borderRadius: radii.full,
												backgroundColor: isSelected ? "#228be6" : "#f1f3f5",
												border: isSelected
													? "1px solid #228be6"
													: "1px solid #ced4da",
												boxShadow: shadows.md,
												cursor: "pointer",
												whiteSpace: "nowrap",
												transition: "all 0.2s ease",
											}}
										>
											<Text
												size="xs"
												fw={600}
												c={isSelected ? "white" : "gray.7"}
											>
												{statusLabels[status] || status} ({statusCounts[status]}
												)
											</Text>
										</Box>
									);
								})}
							</Box>
						</ScrollArea>
					</Box>

					{/* ── Loading skeletons ── */}
					{isLoading && unifiedCards.length === 0 && (
						<Stack
							gap="sm"
							style={{ animation: "fade-in-up 0.4s ease-out 0.1s both" }}
						>
							{[1, 2, 3].map((i) => (
								<Skeleton key={i} height={100} radius={12} />
							))}
						</Stack>
					)}

					{/* ── Empty state ── */}
					{!isLoading && unifiedCards.length === 0 && (
						<Box
							style={{
								animation: "fade-in-up 0.4s ease-out 0.1s both",
								marginTop: 32,
							}}
						>
							<EmptyState
								icon={
									searchQuery || selectedPropertyType || selectedStatus
										? IconSearch
										: IconBuilding
								}
								title={
									searchQuery || selectedPropertyType || selectedStatus
										? t("listings.emptySearch", "No listings found")
										: t("listings.emptyAll")
								}
								description={
									searchQuery || selectedPropertyType || selectedStatus
										? ""
										: t("listings.emptyDescription")
								}
								actionLabel={
									searchQuery || selectedPropertyType || selectedStatus
										? undefined
										: t("listings.createListing")
								}
								onAction={
									searchQuery || selectedPropertyType || selectedStatus
										? undefined
										: () => navigate("/seller/create")
								}
							/>
						</Box>
					)}

					{/* ── Listing cards ── */}
					<Stack gap="xs">
						{unifiedCards.map((card) => {
							const isEditable = !!card.status;
							const borderLeftColor = card.status
								? statusColors[card.status]
								: undefined;

							const menuActions = isEditable ? (
								<Menu position="bottom-end">
									<Menu.Target>
										<ActionIcon
											variant="subtle"
											radius="xl"
											size="sm"
											style={{ backgroundColor: "var(--mantine-color-gray-0)" }}
											onClick={(e) => {
												e.stopPropagation();
												e.preventDefault();
											}}
										>
											<IconDotsVertical size={16} />
										</ActionIcon>
									</Menu.Target>
									<Menu.Dropdown>
										<Menu.Item
											leftSection={<IconEdit size={14} />}
											onClick={(e) => {
												e.stopPropagation();
												navigate(`/seller/edit/${card.id}`);
											}}
										>
											{t("listings.edit")}
										</Menu.Item>
										{card.status === "active" ? (
											<Menu.Item
												leftSection={<IconPlayerPause size={14} />}
												onClick={(e) => {
													e.stopPropagation();
													pauseListing(card.id);
												}}
											>
												{t("listings.pause")}
											</Menu.Item>
										) : card.status === "paused" ? (
											<Menu.Item
												leftSection={<IconPlayerPlay size={14} />}
												onClick={(e) => {
													e.stopPropagation();
													activateListing(card.id);
												}}
											>
												{t("listings.activate")}
											</Menu.Item>
										) : null}
										<Menu.Divider />
										<Menu.Item
											leftSection={<IconTrash size={14} />}
											color="red"
											onClick={(e) => {
												e.stopPropagation();
												handleDeleteClick(card.id);
											}}
										>
											{t("listings.delete")}
										</Menu.Item>
									</Menu.Dropdown>
								</Menu>
							) : null;

							return (
								<Box key={card.id}>
									<ListingRow
										imageUrl={card.imageUrl}
										price={card.price}
										currency={card.currency}
										description={card.title}
										district={card.district}
										onClick={() => {
											// Seed the swiper purely with the currently SEARCHED/FILTERED array order
											const activeIds = unifiedCards.map((c) => c.id);
											seedListingIds(activeIds);
											seedListingSource("finite");
											navigate(`/listings/${card.id}`);
										}}
										actions={
											<Group gap={4} wrap="nowrap">
												{card.status === "active" && (
													<ActionIcon
														variant="subtle"
														color="orange"
														radius="xl"
														size="sm"
														aria-label={t("promotions.purchase")}
														onClick={(e) => {
															e.stopPropagation();
															setBoostModalListingId(card.id);
														}}
													>
														<IconBolt size={16} />
													</ActionIcon>
												)}
												{menuActions}
											</Group>
										}
									>
										{/* Status + stats row */}
										<Group gap={6} mt={4}>
											{card.status && (
												<Badge
													variant="dot"
													size="xs"
													color={borderLeftColor?.replace("#", "") || "gray"}
													radius="sm"
													style={{
														border: "none",
														background: "#f1f5f9",
														fontWeight: 800,
													}}
												>
													{statusLabels[card.status] || card.status}
												</Badge>
											)}
											<Group gap={4} wrap="nowrap" ml="auto">
												{card.views_count !== undefined && (
													<Group
														gap={2}
														wrap="nowrap"
														bg="#f1f5f9"
														px={6}
														py={2}
														style={{ borderRadius: 6 }}
													>
														<IconEye size={12} color="#64748b" />
														<Text size="10px" c="#334155" fw={700}>
															{card.views_count}
														</Text>
													</Group>
												)}
												{card.contacts_count !== undefined &&
													card.contacts_count > 0 && (
														<Group
															gap={2}
															wrap="nowrap"
															ml={2}
															bg="#f1f5f9"
															px={6}
															py={2}
															style={{ borderRadius: 6 }}
														>
															<IconPhone size={12} color="#64748b" />
															<Text size="10px" c="#334155" fw={700}>
																{card.contacts_count}
															</Text>
														</Group>
													)}
												{card.favorites_count !== undefined &&
													card.favorites_count > 0 && (
														<Group
															gap={2}
															wrap="nowrap"
															ml={2}
															bg="#fff1f2"
															px={6}
															py={2}
															style={{ borderRadius: 6 }}
														>
															<IconHeart size={12} color="#e11d48" />
															<Text size="10px" c="#9f1239" fw={700}>
																{card.favorites_count}
															</Text>
														</Group>
													)}
											</Group>
										</Group>
									</ListingRow>
								</Box>
							);
						})}
					</Stack>
				</Stack>

				<style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

				<Modal
					opened={deleteModalOpen}
					onClose={() => setDeleteModalOpen(false)}
					title={
						<Text
							fw={700}
							size="lg"
							style={{ fontFamily: "Outfit, sans-serif" }}
						>
							{t("listings.deleteTitle", "Delete Listing")}
						</Text>
					}
					centered
					radius={radii.lg}
					overlayProps={{ blur: 4, backgroundOpacity: 0.4 }}
					padding="md"
				>
					<Stack gap="md">
						<Text size="sm" c="dimmed" lh={1.4}>
							{t(
								"listings.deleteConfirm",
								"Are you sure you want to permanently delete this listing?",
							)}
						</Text>
						<Group justify="flex-end" gap="sm">
							<Button
								variant="default"
								onClick={() => setDeleteModalOpen(false)}
								radius="xl"
								size="sm"
								style={{
									border: "none",
									background: surface.muted,
									color: "#475569",
								}}
							>
								{t("listings.cancel")}
							</Button>
							<Button color="red" onClick={confirmDelete} radius="xl" size="sm">
								{t("listings.delete")}
							</Button>
						</Group>
					</Stack>
				</Modal>

				{/* Block phase-2 — boost / promotion purchase modal */}
				<BoostModal
					listingId={boostModalListingId}
					opened={boostModalListingId !== null}
					onClose={() => setBoostModalListingId(null)}
				/>
			</Container>
			<Box
				style={{
					position: "fixed",
					bottom: 84, // slightly above the 72px tall tab bar
					left: 0,
					right: 0,
					pointerEvents: "none",
					zIndex: 100,
					paddingBottom: "var(--safe-area-inset-bottom)",
				}}
			>
				<Box
					style={{
						maxWidth: 500,
						margin: "0 auto",
						padding: "0 12px",
						display: "flex",
						justifyContent: "flex-end",
					}}
				>
					<ActionIcon
						size={56}
						radius="xl"
						style={{
							pointerEvents: "auto",
							background: "#228be6",
							color: "white",
							boxShadow: "0 4px 12px rgba(34, 139, 230, 0.4)",
						}}
						onClick={() => navigate("/seller/create")}
					>
						<IconPlus size={28} stroke={2.2} />
					</ActionIcon>
				</Box>
			</Box>
		</InnerPage>
	);
}

export const SellerListings = {
	route: "/seller/listings",
	Page,
};
