import React, { useEffect, useState, useMemo } from "react";
import {
	Container,
	Stack,
	Text,
	Group,
	Menu,
	ActionIcon,
	Box,
	Skeleton,
	TextInput,
	ScrollArea,
	Portal,
	UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconSearch,
	IconX,
	IconBuilding,
	IconCheck,
	IconTrash,
	IconDotsVertical,
	IconEye,
	IconPhone,
	IconInfoCircle,
	IconArrowLeft,
	IconX as IconXIcon, // Alias to avoid conflict with IconX used in TextInput
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { InnerPage } from "@shared/ui/InnerPage";
import { EmptyState } from "@shared/ui/EmptyState";
import { ListingRow } from "@shared/ui/ListingRow";
import { ListingTikTokSlider } from "@modules/buyer/pages/listing-detail/ui/main/ListingTikTokSlider";
import { radii, shadows } from "@app/styles/theme";
import { translateDistrict } from "@shared/lib/regions";
import {
	fetchSellerOLXListings,
	fetchSellerTelegramListings,
	claimOlxListing,
	claimTelegramListing,
	rejectCrawledListing,
} from "@modules/seller/shared/api/sellerCrawledListings";
import type { OLXListing, TelegramListing } from "@shared/api/types";

type Platform = "all" | "olx" | "telegram";

interface UnifiedCard {
	id: string;
	source: Platform;
	price: number;
	currency: string;
	title: string;
	imageUrl: string | null;
	images: { url: string }[];
	rooms: number | null;
	area: number | null;
	district: string | null;
	views_count?: number;
	contacts_count?: number;
}

function Page() {
	const { t } = useTranslation("seller");
	const { t: tBuyer } = useTranslation("buyer");

	const [searchQuery, setSearchQuery] = useState("");
	const [selectedPlatform, setSelectedPlatform] = useState<Platform>("all");
	const [showInfo, setShowInfo] = useState(true); // () => localStorage.getItem('hide_found_info') !== 'true'
	const [activeListingId, setActiveListingId] = useState<string | null>(null);

	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);
	const [reloadTick, setReloadTick] = useState(0);
	const [olxListings, setOlxListings] = useState<OLXListing[]>([]);
	const [telegramListings, setTelegramListings] = useState<TelegramListing[]>(
		[],
	);

	useEffect(() => {
		let active = true;
		const controller = new AbortController();
		const timeout = setTimeout(() => controller.abort(), 15_000);

		const loadListings = async () => {
			setIsLoading(true);
			setHasError(false);
			try {
				if (selectedPlatform === "all") {
					const [resOlx, resTg] = await Promise.all([
						fetchSellerOLXListings({ page: 1, per_page: 50 }),
						fetchSellerTelegramListings({ page: 1, per_page: 50 }),
					]);
					if (active) {
						setOlxListings(resOlx.items);
						setTelegramListings(resTg.items);
					}
				} else if (selectedPlatform === "olx") {
					const res = await fetchSellerOLXListings({ page: 1, per_page: 50 });
					if (active) {
						setOlxListings(res.items);
						setTelegramListings([]);
					}
				} else if (selectedPlatform === "telegram") {
					const res = await fetchSellerTelegramListings({
						page: 1,
						per_page: 50,
					});
					if (active) {
						setTelegramListings(res.items);
						setOlxListings([]);
					}
				}
			} catch (err) {
				console.error("Failed to load crawled listings", err);
				if (active) setHasError(true);
			} finally {
				clearTimeout(timeout);
				if (active) setIsLoading(false);
			}
		};
		loadListings();
		return () => {
			active = false;
			clearTimeout(timeout);
			controller.abort();
		};
	}, [selectedPlatform, reloadTick]);

	const handleReload = () => setReloadTick((n) => n + 1);

	const propertyTypeLabel = (type: string) => {
		const map: Record<string, string> = {
			apartment: t("propertyTypes.apartment", "Apartments"),
			house: t("propertyTypes.house", "Houses"),
			commercial: t("propertyTypes.commercial", "Commercial"),
			land: t("propertyTypes.land", "Land"),
		};
		return map[type] || type;
	};

	const unifiedCards = useMemo((): UnifiedCard[] => {
		const cards: UnifiedCard[] = [];

		if (selectedPlatform === "olx" || selectedPlatform === "all") {
			for (const l of olxListings) {
				const title = `${l.rooms ? `${l.rooms}-${t("listings.rooms")} ` : ""}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t("listings.inDistrict", { district: translateDistrict(l.district, t) })}` : ""}`;

				cards.push({
					id: l.id,
					source: "olx",
					price: l.price,
					currency: l.currency,
					title,
					imageUrl:
						l.images && l.images.length > 0
							? typeof l.images[0] === "string"
								? l.images[0]
								: (l.images[0] as any).url
							: null,
					images: l.images
						? l.images.map((img: any) => ({
								url: typeof img === "string" ? img : img.url,
							}))
						: [],
					rooms: l.rooms,
					area: l.area_sqm,
					district: l.district,
					views_count: l.views_count ?? 0,
				});
			}
		}

		if (selectedPlatform === "telegram" || selectedPlatform === "all") {
			for (const l of telegramListings) {
				const title = `${l.rooms ? `${l.rooms}-${t("listings.rooms")} ` : ""}${propertyTypeLabel(l.property_type)}${l.district ? ` ${t("listings.inDistrict", { district: translateDistrict(l.district, t) })}` : ""}`;

				cards.push({
					id: l.id,
					source: "telegram",
					price: l.price,
					currency: l.currency,
					title,
					imageUrl:
						l.images && l.images.length > 0
							? typeof l.images[0] === "string"
								? l.images[0]
								: (l.images[0] as any).url
							: null,
					images: l.images
						? l.images.map((img: any) => ({
								url: typeof img === "string" ? img : img.url,
							}))
						: [],
					rooms: l.rooms,
					area: l.area_sqm,
					district: l.district,
				});
			}
		}

		if (searchQuery.trim() !== "") {
			const query = searchQuery.toLowerCase();
			return cards.filter(
				(c) =>
					c.title.toLowerCase().includes(query) ||
					(c.district &&
						translateDistrict(c.district, t).toLowerCase().includes(query)),
			);
		}

		return cards;
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [olxListings, telegramListings, selectedPlatform, searchQuery, t]);

	const removeCard = (id: string, source: Platform) => {
		if (source === "olx") {
			setOlxListings((prev) => prev.filter((l) => l.id !== id));
		} else if (source === "telegram") {
			setTelegramListings((prev) => prev.filter((l) => l.id !== id));
		}
		setActiveListingId((curr) => (curr === id ? null : curr));
	};

	// A1 V2.0 — per-card pending state guards against double-click.
	// Map of card_id → "claim" | "reject" while a mutation is in flight.
	const [pendingActions, setPendingActions] = useState<
		Record<string, "claim" | "reject">
	>({});

	const handleClaim = async (e: React.MouseEvent | null, id: string) => {
		if (e) e.stopPropagation();
		if (pendingActions[id]) return; // double-click guard
		const card = unifiedCards.find((c) => c.id === id);
		if (!card || (card.source !== "olx" && card.source !== "telegram")) return;
		const source = card.source;
		setPendingActions((prev) => ({ ...prev, [id]: "claim" }));
		try {
			if (source === "olx") {
				await claimOlxListing(id);
			} else {
				await claimTelegramListing(id);
			}
			removeCard(id, source);
			notifications.show({
				title: t("listings.claimedTitle"),
				message: t("listings.claimedMsg"),
				color: "green",
			});
			// Block C V2.0 (C4) — first-claim hint to add additional phones.
			// Localstorage-gated; shown once per seller.
			if (typeof window !== "undefined") {
				const KEY = "ucm_phones_hint_shown";
				if (!localStorage.getItem(KEY)) {
					localStorage.setItem(KEY, "1");
					setTimeout(() => {
						notifications.show({
							title: t("phones.postClaimHintTitle"),
							message: t("phones.postClaimHintBody"),
							color: "blue",
							autoClose: 8000,
						});
					}, 1500);
				}
			}
		} catch (err: any) {
			const status = err?.response?.status;
			const detail = err?.response?.data?.detail;
			// 409 = already claimed by someone else (per A1 spec)
			const message =
				status === 409
					? t("listings.alreadyClaimedByOther")
					: detail || t("listings.claimFailedMsg");
			notifications.show({
				title: t("listings.claimFailedTitle"),
				message,
				color: "red",
			});
			// On 409 also remove the card — it isn't ours anymore
			if (status === 409) removeCard(id, source);
		} finally {
			setPendingActions((prev) => {
				const next = { ...prev };
				delete next[id];
				return next;
			});
		}
	};

	const handleReject = async (e: React.MouseEvent | null, id: string) => {
		if (e) e.stopPropagation();
		if (pendingActions[id]) return; // double-click guard
		const card = unifiedCards.find((c) => c.id === id);
		if (!card || (card.source !== "olx" && card.source !== "telegram")) return;
		const source = card.source;
		setPendingActions((prev) => ({ ...prev, [id]: "reject" }));
		try {
			await rejectCrawledListing(source, id);
			removeCard(id, source);
			notifications.show({
				title: t("listings.rejectedTitle"),
				message: t("listings.rejectedMsg"),
				color: "gray",
			});
		} catch (err: any) {
			const detail = err?.response?.data?.detail;
			notifications.show({
				title: t("listings.rejectFailedTitle"),
				message: detail || t("listings.rejectFailedMsg"),
				color: "red",
			});
		} finally {
			setPendingActions((prev) => {
				const next = { ...prev };
				delete next[id];
				return next;
			});
		}
	};

	const ALL_PLATFORMS: { value: Platform; label: string }[] = [
		{ value: "all", label: t("listings.all") },
		{ value: "olx", label: "OLX" },
		{ value: "telegram", label: "Telegram" },
	];

	const displayedCards = unifiedCards;

	const listingsMap = useMemo(() => {
		const map: Record<string, any> = {};
		displayedCards.forEach((c) => {
			map[c.id] = {
				id: c.id,
				source: c.source,
				price: c.price,
				currency: c.currency,
				title: c.title,
				description: c.title,
				property_type: "apartment", // placeholder
				type: "sell",
				images: c.images,
				favorites_count: 0,
				views_count: c.views_count || 0,
				rooms: c.rooms,
				area: c.area,
				district: c.district,
			};
		});
		return map;
	}, [displayedCards]);

	const slideIds = displayedCards.map((c) => c.id);

	return (
		<InnerPage title={t("dashboard.found")} noPadding>
			<Container px="md" py="md">
				<Stack gap={16}>
					{/* Informational block */}
					{showInfo && (
						<Box style={{ animation: "fade-in 0.4s ease-out" }}>
							<Box
								style={{
									background: "#f0f9ff",
									border: "1px solid #bae6fd",
									borderRadius: radii.md,
									padding: 16,
									boxShadow: shadows.sm,
									position: "relative",
								}}
							>
								<ActionIcon
									variant="subtle"
									color="gray"
									size="sm"
									style={{ position: "absolute", top: 8, right: 8 }}
									onClick={() => {
										setShowInfo(false);
										// localStorage.setItem('hide_found_info', 'true');
									}}
								>
									<IconXIcon size={16} />
								</ActionIcon>
								<Group wrap="nowrap" align="flex-start" gap="sm" pr={24}>
									<Box style={{ color: "#0284c7", marginTop: 2 }}>
										<IconInfoCircle size={22} stroke={2} />
									</Box>
									<Box style={{ flex: 1 }}>
										<Text size="sm" fw={700} c="dark.9">
											{t("listings.crawledContextTitle")}
										</Text>
										<Text size="13px" mt={4} fw={500} c="dimmed" lh={1.4}>
											{t("listings.crawledContextDesc")}
										</Text>
									</Box>
								</Group>
							</Box>
						</Box>
					)}

					<Box style={{ animation: "fade-in 0.4s ease-out 0.1s both" }}>
						<TextInput
							placeholder={tBuyer("search.title", "Поиск")}
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
								{ALL_PLATFORMS.map((platform) => {
									const isSelected = selectedPlatform === platform.value;
									return (
										<Box
											key={platform.value}
											onClick={() => setSelectedPlatform(platform.value)}
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
												{platform.label}
											</Text>
										</Box>
									);
								})}
							</Box>
						</ScrollArea>
					</Box>

					{isLoading && displayedCards.length === 0 && (
						<Stack
							gap="sm"
							style={{ animation: "fade-in-up 0.4s ease-out 0.1s both" }}
						>
							{[1, 2, 3].map((i) => (
								<Skeleton key={i} height={100} radius={12} />
							))}
						</Stack>
					)}

					{!isLoading && hasError && (
						<Box
							style={{
								animation: "fade-in-up 0.4s ease-out 0.1s both",
								marginTop: 32,
							}}
						>
							<EmptyState
								icon={IconInfoCircle}
								title={t("listings.loadErrorTitle")}
								description={t("listings.loadErrorDesc")}
								actionLabel={t("listings.reloadBtn")}
								onAction={handleReload}
							/>
						</Box>
					)}

					{!isLoading && !hasError && displayedCards.length === 0 && (
						<Box
							style={{
								animation: "fade-in-up 0.4s ease-out 0.1s both",
								marginTop: 32,
							}}
						>
							<EmptyState
								icon={searchQuery ? IconSearch : IconBuilding}
								title={
									searchQuery
										? t("listings.emptySearch")
										: t("listings.emptySource")
								}
								description=""
							/>
						</Box>
					)}

					<Stack gap="xs">
						{displayedCards.map((card) => {
							const isPending = !!pendingActions[card.id];
							const menuActions = (
								<Menu position="bottom-end" disabled={isPending}>
									<Menu.Target>
										<ActionIcon
											variant="subtle"
											radius="xl"
											size="sm"
											disabled={isPending}
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
											leftSection={<IconCheck size={14} />}
											color="blue"
											disabled={isPending}
											onClick={(e) => handleClaim(e, card.id)}
										>
											{t("listings.claimBtn")}
										</Menu.Item>
										<Menu.Divider />
										<Menu.Item
											leftSection={<IconTrash size={14} />}
											color="red"
											disabled={isPending}
											onClick={(e) => handleReject(e, card.id)}
										>
											{t("listings.rejectBtn")}
										</Menu.Item>
									</Menu.Dropdown>
								</Menu>
							);

							return (
								<Box
									key={card.id}
									onClick={() => setActiveListingId(card.id)}
									style={{ cursor: "pointer" }}
								>
									<ListingRow
										imageUrl={card.imageUrl}
										price={card.price}
										currency={card.currency}
										description={card.title}
										district={card.district}
										actions={
											<Group gap={4} wrap="nowrap">
												{menuActions}
											</Group>
										}
									>
										<Group gap={6} mt={4}>
											<Group gap={4} wrap="nowrap">
												{card.views_count !== undefined &&
													card.views_count > 0 && (
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
			</Container>
			{activeListingId && (
				<Portal>
					<Box
						style={{
							position: "fixed",
							inset: 0,
							zIndex: 20000,
							backgroundColor: "#000",
						}}
					>
						<ListingTikTokSlider
							slideIds={slideIds}
							listingsMap={listingsMap}
							initialListingId={activeListingId}
							onLoadMore={() => {}}
							hasMore={false}
							mode="seller-crawled"
							onClaim={(id) => handleClaim(null, id)}
							onReject={(id) => handleReject(null, id)}
						/>
						<Box
							style={{
								position: "fixed",
								bottom: 0,
								left: 0,
								right: 0,
								paddingBottom: "var(--safe-area-inset-bottom)",
								zIndex: 20001,
								pointerEvents: "none",
							}}
						>
							<Box
								style={{
									maxWidth: 500,
									margin: "0 auto",
									position: "relative",
									height: 72, // 4px top + 56px button + 12px bottom
								}}
							>
								<UnstyledButton
									onClick={() => setActiveListingId(null)}
									style={{
										position: "absolute",
										bottom: 12,
										right: 12,
										width: 56,
										height: 56,
										borderRadius: "50%",
										backgroundColor: "rgba(255, 255, 255, 0.65)",
										backdropFilter: "blur(20px) saturate(180%)",
										WebkitBackdropFilter: "blur(20px) saturate(180%)",
										border: "1px solid rgba(255, 255, 255, 0.5)",
										boxShadow: shadows.md,
										pointerEvents: "auto",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconArrowLeft size={24} stroke={1.8} color="#495057" />
								</UnstyledButton>
							</Box>
						</Box>
					</Box>
				</Portal>
			)}
		</InnerPage>
	);
}

export const Found = {
	route: "/seller/found",
	Page,
};
