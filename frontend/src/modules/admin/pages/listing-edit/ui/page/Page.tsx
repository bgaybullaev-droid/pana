/**
 * PR-F.3 — Admin-scoped listing edit page.
 *
 * Reuses the seller's matrix-aware `ListingFormFields` for the entire
 * field surface (S1–S8 + dual-read); the admin variant swaps the save
 * path to `PATCH /admin/listings/{id}` and the ownership check is
 * bypassed server-side.
 *
 * Why not a from-scratch admin form?
 *   - The visibility matrix is already the single source of truth;
 *     duplicating it here would create drift.
 *   - `buildListingData` already implements the S5 dual-read submit
 *     rule (strips `building_type` / `is_furnished`).
 *   - Edit-mode pre-fill logic is already tested in the seller page.
 *
 * The only admin-specific concerns:
 *   - Use the admin-scoped save effect.
 *   - Show a pending-notification after save to mirror admin UX.
 *   - Navigate back to `/admin/listings/:id` instead of `/seller/...`.
 */

import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Box,
	Button,
	Container,
	Group,
	LoadingOverlay,
	Skeleton,
	Stack,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	$editError,
	$editingListing,
	$isLoadingEdit,
	fetchListingForEdit,
	resetEditState,
} from "@shared/state/listing/model";
import { useListingForm } from "@modules/seller/feature/listing-form/ui/useListingForm";
import { ListingFormFields } from "@modules/seller/feature/listing-form/ui/ListingFormFields";
import { updateListingAsAdminFx } from "@modules/admin/shared/state";

function Page() {
	const navigate = useNavigate();
	const { id } = useParams<{ id: string }>();
	const { t: tAdmin } = useTranslation("admin");
	const [editingListing, isLoading, editError] = useUnit([
		$editingListing,
		$isLoadingEdit,
		$editError,
	]);
	const [isSaving] = useUnit([updateListingAsAdminFx.pending]);
	const initializedRef = useRef<string | null>(null);

	const { form, regions, districts, handleRegionChange, buildListingData, t } =
		useListingForm("edit");

	useEffect(() => {
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			fetchListingForEdit(id);
		}
		return () => {
			resetEditState();
		};
	}, [id]);

	// Pre-fill — mirrors seller edit-listing page (see PR-F S5 mapping).
	useEffect(() => {
		if (!editingListing) return;
		const mappedMarketType =
			editingListing.market_type || editingListing.building_type || undefined;
		const mappedFurniture =
			editingListing.furniture ||
			(editingListing.is_furnished === true
				? "full"
				: editingListing.is_furnished === false
					? "none"
					: undefined);
		form.setValues({
			type: editingListing.type as "sell" | "rent",
			property_type: editingListing.property_type as
				| "apartment"
				| "house"
				| "commercial"
				| "land",
			title: editingListing.title || "",
			description: editingListing.description || "",
			price: editingListing.price,
			currency: editingListing.currency as "USD" | "UZS",
			is_negotiable: editingListing.is_negotiable ?? editingListing.price === 0,
			rooms: editingListing.rooms ?? undefined,
			area: editingListing.area ?? undefined,
			living_area: editingListing.living_area ?? undefined,
			kitchen_area: editingListing.kitchen_area ?? undefined,
			land_area: editingListing.land_area ?? undefined,
			floor: editingListing.floor ?? undefined,
			total_floors: editingListing.total_floors ?? undefined,
			condition: editingListing.condition || undefined,
			house_type: editingListing.house_type || undefined,
			house_condition: editingListing.house_condition || [],
			location_type: editingListing.location_type || [],
			water_supply: editingListing.water_supply || [],
			electricity: editingListing.electricity || undefined,
			heating: editingListing.heating || [],
			gas_supply: editingListing.gas_supply || undefined,
			sewage: editingListing.sewage || undefined,
			land_purpose: editingListing.land_purpose || undefined,
			amenities: editingListing.amenities || [],
			nearby_amenities: editingListing.nearby_amenities || [],
			rent_period: editingListing.rent_period || undefined,
			deposit: editingListing.deposit ?? undefined,
			utilities_incl: editingListing.utilities_incl ?? undefined,
			min_rent_months: editingListing.min_rent_months ?? undefined,
			allowed_students: editingListing.allowed_students ?? undefined,
			allowed_pets: editingListing.allowed_pets ?? undefined,
			rent_payment: editingListing.rent_payment || [],
			mortgage_ok: editingListing.mortgage_ok ?? false,
			installment_ok: editingListing.installment_ok ?? false,
			halol_ok: editingListing.halol_ok ?? false,
			deed_type: editingListing.deed_type || undefined,
			urgent_flag: editingListing.urgent_flag ?? false,
			city: editingListing.city || "",
			microdistrict: editingListing.microdistrict || undefined,
			jk_name: editingListing.jk_name || undefined,
			landmark: editingListing.landmark || undefined,
			metro_station: editingListing.metro_station || undefined,
			seller_telegram: editingListing.seller_telegram || undefined,
			commercial_type: editingListing.commercial_type || undefined,
			price_per_sqm: editingListing.price_per_sqm ?? undefined,
			ceiling_height: editingListing.ceiling_height ?? undefined,
			entrance: editingListing.entrance || undefined,
			parking_comm: editingListing.parking_comm ?? undefined,
			building_class: editingListing.building_class || undefined,
			market_type: mappedMarketType,
			wall_material: editingListing.wall_material || undefined,
			furniture: mappedFurniture,
			garage: editingListing.garage ?? undefined,
			basement: editingListing.basement ?? undefined,
			buildings_exist: editingListing.buildings_exist ?? undefined,
			fence: editingListing.fence ?? undefined,
			land_shape: editingListing.land_shape || undefined,
			balcony: editingListing.balcony || undefined,
			listing_subtype: editingListing.listing_subtype || undefined,
			floor_plan_url: editingListing.floor_plan_url || undefined,
			jk_id: editingListing.jk_id || undefined,
			region: editingListing.region || "",
			district: editingListing.district || "",
			address: editingListing.address || "",
			latitude: editingListing.latitude ?? undefined,
			longitude: editingListing.longitude ?? undefined,
			phone: editingListing.phone || "",
			seller_type: editingListing.seller_type || "",
		});
	}, [editingListing]);

	useEffect(() => {
		if (editError) {
			notifications.show({
				title: t("notifications.error"),
				message: editError,
				color: "red",
			});
			resetEditState();
		}
	}, [editError, t]);

	const handleSubmit = async (values: typeof form.values) => {
		if (!id) return;
		try {
			// buildListingData already strips legacy dual-read names + serialises
			// every S3–S8 field correctly. Admin PATCH accepts the same shape.
			const data = buildListingData(values);
			await updateListingAsAdminFx({ listingId: id, data });
			notifications.show({
				title: tAdmin("listingEdit.savedTitle"),
				message: tAdmin("listingEdit.savedMessage"),
				color: "green",
			});
			navigate(`/admin/listings/${id}`);
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : String(e);
			notifications.show({
				title: tAdmin("listingEdit.saveFailed"),
				message: msg,
				color: "red",
			});
		}
	};

	if (isLoading) {
		return (
			<Container size={980} px="md" py="md">
				<Stack gap="md">
					<Skeleton height={32} width={280} />
					<Skeleton height={120} radius={12} />
					<Skeleton height={180} radius={12} />
					<Skeleton height={180} radius={12} />
				</Stack>
			</Container>
		);
	}

	return (
		<Container size={980} px="md" py="md">
			<LoadingOverlay visible={isSaving} />
			<Stack gap="md">
				<Group justify="space-between">
					<Title order={2}>{tAdmin("listingEdit.title")}</Title>
					<Button
						variant="subtle"
						onClick={() => navigate(`/admin/listings/${id}`)}
					>
						{tAdmin("common.back")}
					</Button>
				</Group>

				<Box
					style={{
						border: "1px solid #e9ecef",
						borderRadius: 12,
						padding: 8,
					}}
				>
					<form onSubmit={form.onSubmit(handleSubmit)}>
						<ListingFormFields
							form={form}
							regions={regions}
							districts={districts}
							onRegionChange={handleRegionChange}
						/>
						<Group justify="flex-end" mt="md" mb="sm" mr="sm">
							<Button
								variant="subtle"
								onClick={() => navigate(`/admin/listings/${id}`)}
								disabled={isSaving}
							>
								{tAdmin("common.cancel")}
							</Button>
							<Button type="submit" color="blue" loading={isSaving}>
								{tAdmin("listingEdit.saveChanges")}
							</Button>
						</Group>
					</form>
				</Box>
			</Stack>
		</Container>
	);
}

export const AdminListingEdit = {
	route: "/admin/listings/:id/edit",
	Page,
};
