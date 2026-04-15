import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useUnit } from "effector-react";
import {
	Container,
	Stack,
	FileButton,
	Image,
	SimpleGrid,
	Box,
	ActionIcon,
	Text,
	Button,
	LoadingOverlay,
	Skeleton,
	Badge,
	Group,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconX, IconCameraPlus } from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import { useTelegram } from "@app/providers/useTelegram";
import { useEffectorNotification } from "@shared/hooks/useEffectorNotification";
import { FormSection } from "@shared/ui/FormSection";
import {
	fetchListingForEdit,
	updateListing,
	updateListingFx,
	$editingListing,
	$isLoadingEdit,
	$isUpdating,
	$editError,
	resetEditState,
	type ListingUpdateData,
} from "@shared/state/listing/model";
import { useListingForm } from "@modules/seller/feature/listing-form/ui/useListingForm";
import { ListingFormFields } from "@modules/seller/feature/listing-form/ui/ListingFormFields";
import { radii, surface } from "@app/styles/theme";

function Page() {
	const navigate = useNavigate();
	const { id } = useParams<{ id: string }>();
	const { webApp } = useTelegram();
	const [editingListing, isLoading, isUpdating, editError] = useUnit([
		$editingListing,
		$isLoadingEdit,
		$isUpdating,
		$editError,
	]);
	const initializedRef = useRef<string | null>(null);
	const photoSectionRef = useRef<HTMLDivElement>(null);
	const [imageError, setImageError] = useState(false);

	const {
		form,
		images,
		isUploading,
		regions,
		districts,
		handleRegionChange,
		handleAddImages,
		handleRemoveImage,
		handleUploadImages,
		buildListingData,
		t,
	} = useListingForm("edit");

	useEffect(() => {
		if (id && initializedRef.current !== id) {
			initializedRef.current = id;
			fetchListingForEdit(id);
		}
		return () => {
			resetEditState();
		};
	}, [id]);

	useEffect(() => {
		if (editingListing) {
			console.log("RAW_API_RESPONSE_LISTING:", editingListing);
			// S5 dual-read edit pre-fill: if a legacy listing has only the
			// old columns populated, map them to the new canonical names so
			// the form's market_type/furniture controls show the right value.
			// Backend response already mirrors both names; we pick whichever
			// is non-null.
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
				is_negotiable:
					editingListing.is_negotiable ?? editingListing.price === 0,
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
				// Sprint 2 — rent group
				rent_period: editingListing.rent_period || undefined,
				deposit: editingListing.deposit ?? undefined,
				utilities_incl: editingListing.utilities_incl ?? undefined,
				min_rent_months: editingListing.min_rent_months ?? undefined,
				allowed_students: editingListing.allowed_students ?? undefined,
				allowed_pets: editingListing.allowed_pets ?? undefined,
				rent_payment: editingListing.rent_payment || [],
				// Sprint 2 — sale finance + deed
				mortgage_ok: editingListing.mortgage_ok ?? false,
				installment_ok: editingListing.installment_ok ?? false,
				halol_ok: editingListing.halol_ok ?? false,
				deed_type: editingListing.deed_type || undefined,
				// Sprint 3 — cross-cutting location (T-001)
				urgent_flag: editingListing.urgent_flag ?? false,
				city: editingListing.city || "",
				microdistrict: editingListing.microdistrict || undefined,
				jk_name: editingListing.jk_name || undefined,
				landmark: editingListing.landmark || undefined,
				metro_station: editingListing.metro_station || undefined,
				seller_telegram: editingListing.seller_telegram || undefined,
				// Sprint 4 — commercial (T-009)
				commercial_type: editingListing.commercial_type || undefined,
				price_per_sqm: editingListing.price_per_sqm ?? undefined,
				ceiling_height: editingListing.ceiling_height ?? undefined,
				entrance: editingListing.entrance || undefined,
				parking_comm: editingListing.parking_comm ?? undefined,
				building_class: editingListing.building_class || undefined,
				// Sprint 5 — dual-read new columns (mapped from old on legacy rows)
				market_type: mappedMarketType,
				wall_material: editingListing.wall_material || undefined,
				furniture: mappedFurniture,
				// Sprint 6 — property polish
				garage: editingListing.garage ?? undefined,
				basement: editingListing.basement ?? undefined,
				buildings_exist: editingListing.buildings_exist ?? undefined,
				fence: editingListing.fence ?? undefined,
				land_shape: editingListing.land_shape || undefined,
				balcony: editingListing.balcony || undefined,
				listing_subtype: editingListing.listing_subtype || undefined,
				floor_plan_url: editingListing.floor_plan_url || undefined,
				// Sprint 7 — housing complex linkage
				jk_id: editingListing.jk_id || undefined,
				region: editingListing.region || "",
				district: editingListing.district || "",
				address: editingListing.address || "",
				latitude: editingListing.latitude ?? undefined,
				longitude: editingListing.longitude ?? undefined,
				phone: editingListing.phone || "",
				seller_type: editingListing.seller_type || "",
			});
		}
	}, [editingListing]);

	const [existingImagesList, setExistingImagesList] = useState<any[]>([]);

	useEffect(() => {
		if (editingListing?.images) {
			setExistingImagesList(editingListing.images);
		}
	}, [editingListing?.images]);

	const handleRemoveExistingImage = (imageId: string) => {
		setExistingImagesList((prev) => prev.filter((img) => img.id !== imageId));
	};

	useEffectorNotification(
		updateListingFx,
		{
			title: t("notifications.success"),
			message: t("notifications.listingUpdated"),
			color: "green",
		},
		() => {
			webApp?.HapticFeedback.notificationOccurred("success");
			navigate("/seller/listings");
		},
	);

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

	const existingImageCount = existingImagesList.length;
	const totalImageCount = existingImageCount + images.length;

	useEffect(() => {
		if (totalImageCount > 0 && imageError) {
			setImageError(false);
		}
	}, [totalImageCount, imageError]);

	const handleError = () => {
		if (totalImageCount === 0) {
			setImageError(true);
		}
	};

	const handleSubmit = async (values: typeof form.values) => {
		if (!id) return;
		const existingCount = existingImagesList.length;
		const totalImageCount = existingCount + images.length;

		if (totalImageCount === 0) {
			setImageError(true);
			photoSectionRef.current?.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
			return;
		}

		const uploadedImages = await handleUploadImages(existingCount);

		// Transform kept existing images to the creation format
		const keptImages = existingImagesList.map((img, idx) => ({
			original_url: img.original_url,
			thumbnail_url: img.thumbnail_url,
			medium_url: img.medium_url,
			large_url: img.large_url,
			position: idx,
			is_primary: idx === 0,
		}));

		const finalImages = [...keptImages, ...uploadedImages]
			.slice(0, 10)
			.map((img, idx) => ({
				...img,
				position: idx,
				is_primary: idx === 0,
			}));

		const originalImageIds =
			editingListing?.images?.map((i) => i.id).join(",") || "";
		const currentImageIds = existingImagesList.map((i) => i.id).join(",");
		const isImagesModified =
			originalImageIds !== currentImageIds || uploadedImages.length > 0;

		const listingData: ListingUpdateData = {
			...buildListingData(values),
			images: isImagesModified ? finalImages : undefined,
		};

		updateListing({ id, data: listingData });
	};

	if (isLoading) {
		return (
			<Container size={980} px="md" py="md">
				<Stack gap="md">
					<Group gap="sm">
						<Skeleton width={30} height={30} circle />
						<Skeleton width={180} height={28} />
					</Group>
					<Skeleton height={80} radius={12} />
					<Skeleton height={120} radius={12} />
					<Skeleton height={80} radius={12} />
					<Skeleton height={80} radius={12} />
					<Skeleton height={80} radius={12} />
				</Stack>
			</Container>
		);
	}

	const errorCount =
		Object.keys(form.errors).length +
		(totalImageCount === 0 && imageError ? 1 : 0);

	return (
		<InnerPage title={t("editListing.title")} noPadding>
			<Container px="md" pt="md" pb={160}>
				<LoadingOverlay visible={isUpdating || isUploading} />
				<form onSubmit={form.onSubmit(handleSubmit, handleError)}>
					<Stack gap="md">
						{/* Section: Photos */}
						<div ref={photoSectionRef}>
							<FormSection title={t("createListing.photos")} required>
								{/* Existing images */}
								{existingImagesList.length > 0 && (
									<Box mb="sm">
										<Text size="12px" c="dimmed" mb={6} fw={500}>
											{t("editListing.currentPhotos")}
										</Text>
										<SimpleGrid cols={3} spacing="xs">
											{existingImagesList.map((image) => (
												<Box
													key={image.id}
													style={{
														position: "relative",
														aspectRatio: "1",
														borderRadius: radii.md,
														overflow: "hidden",
														border: "1px solid #f1f5f9",
													}}
												>
													<Image
														src={image.medium_url || image.original_url}
														alt=""
														fit="cover"
														h="100%"
													/>
													<ActionIcon
														variant="filled"
														color="red"
														size="sm"
														radius="xl"
														style={{ position: "absolute", top: 4, right: 4 }}
														onClick={() => handleRemoveExistingImage(image.id)}
													>
														<IconX size={14} />
													</ActionIcon>
												</Box>
											))}
										</SimpleGrid>
									</Box>
								)}

								{/* New images */}
								<Box>
									<Group justify="space-between" mb={6}>
										<Text size="12px" c="dimmed" fw={500}>
											{t("editListing.addNewPhotos")}
										</Text>
										<Badge size="sm" variant="light" color="blue" radius="sm">
											{totalImageCount}/10
										</Badge>
									</Group>
									<SimpleGrid cols={3} spacing="xs">
										{images.map((file, index) => (
											<Box
												key={index}
												style={{
													position: "relative",
													aspectRatio: "1",
													borderRadius: radii.md,
													overflow: "hidden",
													border: "1px solid #f1f5f9",
												}}
											>
												<Image
													src={URL.createObjectURL(file)}
													alt=""
													fit="cover"
													h="100%"
												/>
												<ActionIcon
													variant="filled"
													color="red"
													size="sm"
													radius="xl"
													style={{ position: "absolute", top: 4, right: 4 }}
													onClick={() => handleRemoveImage(index)}
												>
													<IconX size={14} />
												</ActionIcon>
											</Box>
										))}
										{totalImageCount < 10 && (
											<FileButton
												onChange={handleAddImages}
												accept="image/*"
												multiple
											>
												{(props) => (
													<Box
														{...props}
														style={{
															aspectRatio: "1",
															borderRadius: radii.md,
															border: "2px dashed #cbd5e1",
															backgroundColor: surface.page,
															display: "flex",
															alignItems: "center",
															justifyContent: "center",
															cursor: "pointer",
														}}
													>
														<IconCameraPlus
															size={22}
															color="#94a3b8"
															stroke={1.5}
														/>
													</Box>
												)}
											</FileButton>
										)}
									</SimpleGrid>
								</Box>
								{imageError && totalImageCount === 0 && (
									<Text size="13px" c="red" mt={4}>
										{t("validation.imagesRequired") ||
											"Добавьте хотя бы одно фото"}
									</Text>
								)}
							</FormSection>
						</div>

						{/* Shared form fields: Type, Main Info, Parameters, Location, Price, Contact */}
						<ListingFormFields
							form={form}
							regions={regions}
							districts={districts}
							onRegionChange={handleRegionChange}
						/>
					</Stack>
				</form>

				{/* Fixed Action Buttons Panel */}
				<Box
					style={{
						position: "fixed",
						bottom: 0,
						left: 0,
						right: 0,
						paddingBottom: "env(safe-area-inset-bottom, 0px)",
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
						{errorCount > 0 && (
							<Box
								style={{
									backgroundColor: "#fee2e2",
									border: "1px solid #fca5a5",
									padding: "10px 16px",
									borderRadius: 20,
									marginBottom: 12,
									pointerEvents: "auto",
									boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
								}}
							>
								<Text size="xs" c="red.8" fw={500} ta="center">
									{t("createListing.unfilledFieldsSummary", {
										count: errorCount,
										defaultValue: `Осталось заполнить ${errorCount} полей. Прокрутите вверх.`,
									})}
								</Text>
							</Box>
						)}
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
								onClick={() => navigate(-1)}
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
								{t("createListing.cancel")}
							</Button>
							<Button
								type="submit"
								style={{ flex: 1 }}
								h="100%"
								radius={100}
								c="white"
								fw={600}
								fz={14}
								loading={isUpdating || isUploading}
								onClick={() => form.onSubmit(handleSubmit, handleError)()}
								styles={{
									root: {
										backgroundColor: "rgba(64, 167, 227, 0.55)",
										backdropFilter: "blur(20px) saturate(180%)",
										WebkitBackdropFilter: "blur(20px) saturate(180%)",
										boxShadow: "0 4px 15px rgba(64, 167, 227, 0.4)",
										border: "1px solid rgba(255, 255, 255, 0.2)",
									},
								}}
							>
								{isUploading
									? t("createListing.uploadingPhotos")
									: t("editListing.save")}
							</Button>
						</Box>
					</Box>
				</Box>
			</Container>
		</InnerPage>
	);
}

export const EditListing = {
	route: "/seller/edit/:id",
	Page,
};
