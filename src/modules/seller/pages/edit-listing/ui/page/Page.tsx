import { useEffect, useRef } from "react";
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
import { radii, shadows, spacing, surface } from "@app/styles/theme";

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
	const errorShownRef = useRef<string | null>(null);

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
	} = useListingForm();

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
				rooms: editingListing.rooms ?? undefined,
				area: editingListing.area ?? undefined,
				floor: editingListing.floor ?? undefined,
				total_floors: editingListing.total_floors ?? undefined,
				region: editingListing.region || "",
				district: editingListing.district || "",
				address: editingListing.address || "",
				phone: editingListing.phone || "",
			});
		}
	}, [editingListing]);

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
		if (editError && errorShownRef.current !== editError) {
			errorShownRef.current = editError;
			notifications.show({
				title: t("notifications.error"),
				message: editError,
				color: "red",
			});
		}
	}, [editError, t]);

	const handleSubmit = async (values: typeof form.values) => {
		if (!id) return;
		const existingCount = editingListing?.images?.length || 0;
		const uploadedImages = await handleUploadImages(existingCount);

		const listingData: ListingUpdateData = {
			...buildListingData(values),
			images: uploadedImages.length > 0 ? uploadedImages : undefined,
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

	const existingImageCount = editingListing?.images?.length || 0;
	const totalImageCount = existingImageCount + images.length;

	return (
		<InnerPage title={t("editListing.title")} noPadding>
			<Container px="sm" py="md">
			<LoadingOverlay visible={isUpdating || isUploading} />
			<form onSubmit={form.onSubmit(handleSubmit)}>
				<Stack gap="md">

					{/* Shared form fields: Type, Main Info, Price, Parameters, Location, Contact */}
					<ListingFormFields
						form={form}
						regions={regions}
						districts={districts}
						onRegionChange={handleRegionChange}
					/>

					{/* Section: Photos */}
					<FormSection title={t("createListing.photos")}>
						{/* Existing images */}
						{editingListing?.images && editingListing.images.length > 0 && (
							<Box mb="sm">
								<Text size="12px" c="dimmed" mb={6} fw={500}>
									{t("editListing.currentPhotos")}
								</Text>
								<SimpleGrid cols={3} spacing="xs">
									{editingListing.images.map((image) => (
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
					</FormSection>

					{/* Spacer for sticky button */}
					<Box style={{ height: 70 }} />
				</Stack>
			</form>

			{/* Sticky Submit Button */}
			<Box
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					padding: spacing.card,
					paddingBottom: "calc(16px + env(safe-area-inset-bottom, 0px))",
					backgroundColor: "rgba(255,255,255,0.9)",
					backdropFilter: "blur(8px)",
					WebkitBackdropFilter: "blur(8px)",
					zIndex: 999,
					borderTop: "1px solid #f1f5f9",
				}}
			>
				<Box style={{ maxWidth: 980, margin: "0 auto" }}>
					<Button
						type="submit"
						size="md"
						fullWidth
						radius={radii.md}
						loading={isUpdating || isUploading}
						onClick={() => form.onSubmit(handleSubmit)()}
						style={{
							background: "#228be6",
							border: "none",
							boxShadow: shadows.accent,
						}}
					>
						{isUploading
							? t("createListing.uploadingPhotos")
							: t("editListing.save")}
					</Button>
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
