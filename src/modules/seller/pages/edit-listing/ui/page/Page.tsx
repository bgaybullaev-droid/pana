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
import { IconX, IconCameraPlus, IconArrowLeft } from "@tabler/icons-react";
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
			<Container size="sm" px="md" py="md">
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
		<Container
			px="sm"
			py="md"
			style={{
				backgroundColor: "#f8fafc",
				minHeight: "100vh",
				maxWidth: 480,
				margin: "0 auto",
				overflow: "auto",
			}}
		>
			<LoadingOverlay visible={isUpdating || isUploading} />
			<form onSubmit={form.onSubmit(handleSubmit)}>
				<Stack gap="md">
					{/* Header */}
					<Group gap="sm" align="center" mb="xs">
						<ActionIcon
							variant="transparent"
							color="dark.9"
							size={36}
							radius="md"
							onClick={() => navigate(-1)}
						>
							<IconArrowLeft size={20} />
						</ActionIcon>
						<Text
							size="xl"
							fw={800}
							style={{
								fontFamily: "Outfit, sans-serif",
								letterSpacing: "-0.3px",
							}}
							c="dark.9"
						>
							{t("editListing.title")}
						</Text>
					</Group>

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
												borderRadius: 12,
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
											borderRadius: 12,
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
													borderRadius: 12,
													border: "2px dashed #cbd5e1",
													backgroundColor: "#f8fafc",
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
					padding: "16px",
					paddingBottom: "calc(16px + env(safe-area-inset-bottom, 0px))",
					backgroundColor: "rgba(255,255,255,0.9)",
					backdropFilter: "blur(8px)",
					WebkitBackdropFilter: "blur(8px)",
					zIndex: 999,
					borderTop: "1px solid #f1f5f9",
				}}
			>
				<Box style={{ maxWidth: 448, margin: "0 auto" }}>
					<Button
						type="submit"
						size="md"
						fullWidth
						radius={12}
						loading={isUpdating || isUploading}
						onClick={() => form.onSubmit(handleSubmit)()}
						style={{
							background: "#228be6",
							border: "none",
							boxShadow: "0 4px 12px rgba(34, 139, 230, 0.2)",
						}}
					>
						{isUploading
							? t("createListing.uploadingPhotos")
							: t("editListing.save")}
					</Button>
				</Box>
			</Box>
		</Container>
	);
}

export const EditListing = {
	route: "/seller/edit/:id",
	Page,
};
