import { useState, useMemo } from "react";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useTranslation } from "react-i18next";
import {
	uploadImageFx,
	type ListingImageCreateData,
} from "@shared/state/listing/model";
import {
	getRegionOptions,
	getDistrictOptions,
} from "@shared/constants/regions";

export interface ListingFormValues {
	type: "sell" | "rent";
	property_type: "apartment" | "house" | "commercial" | "land";
	title: string;
	description: string;
	price: number | undefined;
	currency: "USD" | "UZS";
	is_negotiable: boolean;
	// Dimensions
	rooms: number | undefined;
	area: number | undefined;
	living_area: number | undefined;
	kitchen_area: number | undefined;
	land_area: number | undefined;
	floor: number | undefined;
	total_floors: number | undefined;
	// Apartment attributes
	building_type: string | undefined;
	condition: string | undefined;
	// House attributes
	house_type: string | undefined;
	house_condition: string[];
	location_type: string[];
	water_supply: string[];
	electricity: string | undefined;
	heating: string[];
	gas_supply: string | undefined;
	sewage: string | undefined;
	// Common attributes
	is_furnished: string | undefined;
	land_purpose: string | undefined;
	// Amenities
	amenities: string[];
	nearby_amenities: string[];
	// Location
	region: string;
	district: string;
	address: string;
	latitude: number | undefined;
	longitude: number | undefined;
	// Contact
	phone: string;
	seller_type: string;
}

export function useListingForm() {
	const { t } = useTranslation("seller");
	const [images, setImages] = useState<File[]>([]);
	const [isUploading, setIsUploading] = useState(false);
	const [uploadProgress, setUploadProgress] = useState(0);

	const regions = getRegionOptions(t);

	const form = useForm<ListingFormValues>({
		initialValues: {
			type: "sell",
			property_type: "apartment",
			title: "",
			description: "",
			price: undefined,
			currency: "USD",
			is_negotiable: false,
			rooms: undefined,
			area: undefined,
			living_area: undefined,
			kitchen_area: undefined,
			land_area: undefined,
			floor: undefined,
			total_floors: undefined,
			building_type: undefined,
			condition: undefined,
			house_type: undefined,
			house_condition: [],
			location_type: [],
			water_supply: [],
			electricity: undefined,
			heating: [],
			gas_supply: undefined,
			sewage: undefined,
			is_furnished: undefined,
			land_purpose: undefined,
			amenities: [],
			nearby_amenities: [],
			region: "",
			district: "",
			address: "",
			latitude: undefined,
			longitude: undefined,
			phone: "",
			seller_type: "",
		},
		validate: {
			type: (value, values) =>
				values.property_type !== "land" && !value
					? t("validation.dealTypeRequired")
					: null,
			price: (value, values) =>
				!values.is_negotiable && (!value || value <= 0)
					? t("validation.priceRequired")
					: null,
			rooms: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isHouse = values.property_type === "house";
				if ((isApt || isHouse) && value === undefined) {
					return t("validation.roomsRequired");
				}
				return null;
			},
			area: (value, values) => {
				if (values.property_type !== "land" && !value) {
					return t("validation.areaRequired");
				}
				return null;
			},
			floor: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				if ((isApt || isCom) && value === undefined) {
					return t("validation.floorRequired");
				}
				return null;
			},
			total_floors: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				const isHouse = values.property_type === "house";
				if ((isApt || isCom || isHouse) && value === undefined) {
					return t("validation.totalFloorsRequired");
				}
				return null;
			},
			building_type: (value, values) =>
				values.property_type === "apartment" && !value
					? t("validation.buildingTypeRequired")
					: null,
			condition: (value, values) => {
				const isApt = values.property_type === "apartment";
				const isCom = values.property_type === "commercial";
				if ((isApt || isCom) && !value) {
					return t("validation.conditionRequired");
				}
				return null;
			},
			is_furnished: (value, values) =>
				values.property_type !== "land" && !value
					? t("validation.furnishedRequired")
					: null,
			region: (value) => (!value ? t("validation.regionRequired") : null),
			district: (value) => (!value ? t("validation.districtRequired") : null),
			latitude: (value) => (!value ? t("validation.mapRequired") : null),
		},
	});

	const districts = useMemo(
		() => getDistrictOptions(form.values.region, t),
		[form.values.region, t],
	);

	const handleRegionChange = (value: string) => {
		form.setFieldValue("region", value);
		form.setFieldValue("district", "");
	};

	const handleAddImages = (files: File[]) => {
		setImages((prev) => [...prev, ...files].slice(0, 10));
	};

	const handleRemoveImage = (index: number) => {
		setImages((prev) => prev.filter((_, i) => i !== index));
	};

	const uploadImages = async (
		files: File[],
		positionOffset = 0,
	): Promise<ListingImageCreateData[]> => {
		const uploadedImages: ListingImageCreateData[] = [];
		for (let i = 0; i < files.length; i++) {
			setUploadProgress(Math.round((i / files.length) * 100));
			try {
				const uploadResult = await uploadImageFx(files[i]);
				uploadedImages.push({
					original_url: uploadResult.original_url,
					thumbnail_url: uploadResult.thumbnail_url,
					medium_url: uploadResult.medium_url,
					large_url: uploadResult.large_url,
					position: positionOffset + i,
					is_primary: positionOffset === 0 && i === 0,
				});
			} catch (error) {
				console.error(`Failed to upload image ${i + 1}:`, error);
			}
		}
		setUploadProgress(100);
		return uploadedImages;
	};

	const handleUploadImages = async (
		positionOffset = 0,
	): Promise<ListingImageCreateData[]> => {
		if (images.length === 0) return [];
		setIsUploading(true);
		setUploadProgress(0);
		try {
			return await uploadImages(images, positionOffset);
		} catch (error) {
			console.error("Image upload failed:", error);
			notifications.show({
				title: t("notifications.warning"),
				message: t("notifications.imageUploadFailed"),
				color: "yellow",
			});
			return [];
		} finally {
			setIsUploading(false);
		}
	};

	const buildListingData = (values: ListingFormValues) => ({
		type: values.type,
		property_type: values.property_type,
		title: values.title || undefined,
		description: values.description || undefined,
		price: values.is_negotiable ? 0 : values.price!,
		currency: values.currency,
		rooms: values.rooms,
		area: values.area,
		living_area: values.living_area,
		kitchen_area: values.kitchen_area,
		land_area: values.land_area,
		floor: values.floor,
		total_floors: values.total_floors,
		building_type: values.building_type || undefined,
		condition: values.condition || undefined,
		house_type: values.house_type || undefined,
		house_condition:
			values.house_condition.length > 0 ? values.house_condition : undefined,
		location_type:
			values.location_type.length > 0 ? values.location_type : undefined,
		water_supply:
			values.water_supply.length > 0 ? values.water_supply : undefined,
		electricity: values.electricity || undefined,
		heating: values.heating.length > 0 ? values.heating : undefined,
		gas_supply: values.gas_supply || undefined,
		sewage: values.sewage || undefined,
		is_furnished:
			values.is_furnished === "yes"
				? true
				: values.is_furnished === "no"
					? false
					: undefined,
		land_purpose: values.land_purpose || undefined,
		amenities: values.amenities.length > 0 ? values.amenities : undefined,
		nearby_amenities:
			values.nearby_amenities.length > 0 ? values.nearby_amenities : undefined,
		region: values.region,
		district: values.district,
		address: values.address || undefined,
		latitude: values.latitude,
		longitude: values.longitude,
		phone: values.phone || undefined,
		seller_type: values.seller_type || undefined,
	});

	return {
		form,
		images,
		isUploading,
		uploadProgress,
		regions,
		districts,
		handleRegionChange,
		handleAddImages,
		handleRemoveImage,
		handleUploadImages,
		buildListingData,
		t,
	};
}
