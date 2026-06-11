/**
 * Block F V2.0 (F1) — Stage 2: preview-only + publish.
 *
 * AI description editing happens in Stage 1. This screen shows the
 * listing exactly as buyers will see it and lets the seller publish
 * or go back to edit.
 */

import { useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Box,
	Button,
	Container,
	Stack,
	Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconCheck,
	IconPencil,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { apiClient } from "@shared/api/client";
import {
	publishDraftFx,
	type ListingCreateData,
} from "@shared/state/listing/model";
import type { UnifiedListing } from "@shared/api/types";
import { clearDraft } from "@modules/seller/feature/listing-form/ui/listingDraftStorage";
import { ListingSlideContent } from "@modules/buyer/pages/listing-detail/ui/main/ListingSlideContent";

import {
	$draftFormData,
	$draftId,
	$editedDescriptions,
	$isPublishing,
} from "../../model/stores";
import {
	resetDraftFlow,
	stageBackToParams,
} from "../../model/events";

function buildPreviewListing(
	data: ListingCreateData,
	id: string,
): UnifiedListing {
	return {
		source: "main",
		id,
		type: data.type,
		property_type: data.property_type,
		price: data.price,
		currency: data.currency,
		rooms: data.rooms ?? null,
		area: data.area ?? null,
		floor: data.floor ?? null,
		total_floors: data.total_floors ?? null,
		region: data.region ?? null,
		district: data.district,
		address: data.address ?? null,
		latitude: data.latitude ?? null,
		longitude: data.longitude ?? null,
		description: null,
		raw_text: null,
		images: (data.images ?? []).map((img) => ({
			url: img.original_url,
			thumbnail: img.thumbnail_url ?? null,
		})),
		contact_phone: data.phone ?? null,
		created_at: new Date().toISOString(),
		title: null,
		views_count: 0,
		favorites_count: 0,
		comments_count: 0,
		is_favorited: false,
		is_boosted: false,
		is_highlighted: false,
		seller_id: null,
		seller_name: null,
		seller_avatar_url: null,
		seller_verified: false,
		seller_type: data.seller_type ?? null,
		seller_telegram: data.seller_telegram ?? null,
		building_type: data.building_type ?? null,
		condition: data.condition ?? null,
		land_purpose: data.land_purpose ?? null,
		market_type: data.market_type ?? null,
		wall_material: data.wall_material ?? null,
		listing_subtype: data.listing_subtype ?? null,
		balcony: data.balcony ?? null,
		house_type: data.house_type ?? null,
		house_condition: data.house_condition ?? null,
		location_type: data.location_type ?? null,
		living_area: data.living_area ?? null,
		kitchen_area: data.kitchen_area ?? null,
		land_area: data.land_area ?? null,
		furniture: data.furniture ?? null,
		is_furnished: data.is_furnished ?? null,
		garage: data.garage ?? null,
		basement: data.basement ?? null,
		buildings_exist: data.buildings_exist ?? null,
		fence: data.fence ?? null,
		land_shape: data.land_shape ?? null,
		ceiling_height: data.ceiling_height ?? null,
		water_supply: data.water_supply ?? null,
		electricity: data.electricity ?? null,
		heating: data.heating ?? null,
		gas_supply: data.gas_supply ?? null,
		sewage: data.sewage ?? null,
		commercial_type: data.commercial_type ?? null,
		price_per_sqm: data.price_per_sqm ?? null,
		entrance: data.entrance ?? null,
		parking_comm: data.parking_comm ?? null,
		building_class: data.building_class ?? null,
		is_negotiable: data.is_negotiable ?? false,
		deed_type: data.deed_type ?? null,
		urgent_flag: data.urgent_flag ?? false,
		rent_period: data.rent_period ?? null,
		deposit: data.deposit ?? null,
		utilities_incl: data.utilities_incl ?? null,
		min_rent_months: data.min_rent_months ?? null,
		allowed_students: data.allowed_students ?? null,
		allowed_pets: data.allowed_pets ?? null,
		rent_payment: data.rent_payment ?? null,
		mortgage_ok: data.mortgage_ok ?? false,
		installment_ok: data.installment_ok ?? false,
		halol_ok: data.halol_ok ?? false,
		city: data.city ?? null,
		microdistrict: data.microdistrict ?? null,
		jk_name: data.jk_name ?? null,
		landmark: data.landmark ?? null,
		metro_station: data.metro_station ?? null,
		amenities: data.amenities ?? null,
		nearby_amenities: data.nearby_amenities ?? null,
		confidence: null,
		source_url: null,
		original_language: null,
		is_translated: false,
	};
}

function Stage2() {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const { t } = useTranslation("seller");

	const [draftId, draftFormData, edits, isPublishing] = useUnit([
		$draftId,
		$draftFormData,
		$editedDescriptions,
		$isPublishing,
	]);

	// Preview "phone screenshot" frame — drawers opened from the preview
	// render inside this element instead of covering the whole viewport.
	const previewFrameRef = useRef<HTMLDivElement>(null);

	const previewListing = useMemo((): UnifiedListing | null => {
		if (!draftFormData || !draftId) return null;
		return buildPreviewListing(draftFormData, draftId);
	}, [draftFormData, draftId]);

	const handlePublish = async () => {
		if (!draftId) return;
		const description = edits.ru.trim() || undefined;
		try {
			await publishDraftFx({ id: draftId, description });
			webApp?.HapticFeedback.notificationOccurred("success");
			notifications.show({
				title: t("notifications.success"),
				message: t("notifications.listingCreated"),
				color: "green",
			});
			try {
				const res = await apiClient.get<{
					total_active_listings?: number;
					free_listings_per_seller?: number;
					test_period_active?: boolean;
				}>("/sellers/me/dashboard");
				const active = res.data.total_active_listings ?? 0;
				const free = res.data.free_listings_per_seller ?? 0;
				if (active >= 3) {
					notifications.show({
						title: t("notifications.info", "Подождите"),
						message: res.data.test_period_active
							? t("myListings.thirdListingToast", {
									count: active,
									defaultValue:
										"Это ваше {{count}}-е объявление в тестовый период",
								})
							: t("myListings.overFreeLimitToast", {
									count: active,
									free,
									defaultValue:
										"Активных объявлений: {{count}} / {{free}} бесплатных",
								}),
						color: "blue",
						autoClose: 5000,
					});
				}
			} catch {
				/* non-fatal */
			}
			resetDraftFlow();
			clearDraft();
			navigate("/seller/listings");
		} catch {
			notifications.show({
				title: t("notifications.error"),
				message: t(
					"createListing.publishFailed",
					"Не удалось опубликовать. Попробуйте ещё раз.",
				),
				color: "red",
			});
		}
	};

	return (
		<InnerPage
			title={t("createListing.previewPageTitle", "Ваше объявление")}
			noPadding
		>
			<Container px={0} pt="sm" pb={100}>
				<Stack gap="md">
					{/* Subtitle */}
					<Text size="xs" c="dimmed" ta="center" px="md">
						{t(
							"createListing.previewSubtitle",
							"Посмотрите, как будет выглядеть для покупателей",
						)}
					</Text>

					{/* ── Interactive "screenshot" preview frame ── */}
					{previewListing && (
						<Box
							ref={previewFrameRef}
							mx="md"
							style={{
								height: "65vh",
								borderRadius: 20,
								overflow: "hidden",
								boxShadow:
									"0 8px 40px rgba(0,0,0,0.18), 0 2px 12px rgba(0,0,0,0.1)",
								border: "2.5px solid #fff",
								position: "relative",
								// transform creates a new containing block for position:fixed
								// elements portaled inside, keeping drawers within the frame
								transform: "translateZ(0)",
							}}
						>
							<ListingSlideContent
								listing={previewListing}
								isActive={true}
								mode="buyer"
								containerRef={previewFrameRef}
							/>
						</Box>
					)}
				</Stack>
			</Container>

			{/* ── Fixed bottom action panel ── */}
			<Box
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					paddingBottom: "var(--safe-area-inset-bottom)",
					zIndex: 10001,
					pointerEvents: "none",
				}}
			>
				<Box
					style={{
						padding: "4px 12px 12px",
						maxWidth: 500,
						margin: "0 auto",
					}}
				>
					<Box
						style={{
							display: "flex",
							alignItems: "center",
							height: 56,
							pointerEvents: "auto",
							gap: "10px",
						}}
					>
						<Button
							style={{ flex: 1 }}
							h="100%"
							radius={100}
							c="#495057"
							fw={600}
							fz={14}
							leftSection={<IconPencil size={16} />}
							onClick={() => stageBackToParams()}
							styles={{
								root: {
									backgroundColor: "rgba(255, 255, 255, 0.55)",
									backdropFilter: "blur(20px) saturate(180%)",
									WebkitBackdropFilter: "blur(20px) saturate(180%)",
									border: "1px solid rgba(0, 0, 0, 0.12)",
									boxShadow: "0 4px 15px rgba(0,0,0,0.08)",
								},
							}}
						>
							{t("createListing.editButton", "Редактировать")}
						</Button>
						<Button
							style={{ flex: 1.4 }}
							h="100%"
							radius={100}
							c="white"
							fw={600}
							fz={14}
							loading={isPublishing}
							leftSection={<IconCheck size={16} />}
							onClick={handlePublish}
							styles={{
								root: {
									backgroundColor: "rgba(34, 139, 230, 0.85)",
									backdropFilter: "blur(20px) saturate(180%)",
									WebkitBackdropFilter: "blur(20px) saturate(180%)",
									boxShadow: "0 4px 15px rgba(34, 139, 230, 0.4)",
									border: "1px solid rgba(255, 255, 255, 0.2)",
								},
							}}
						>
							{t("createListing.publish", "Опубликовать")}
						</Button>
					</Box>
				</Box>
			</Box>
		</InnerPage>
	);
}

export default Stage2;
