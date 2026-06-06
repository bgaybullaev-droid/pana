import { FC, Fragment, useState, useRef } from "react";
import {
	Drawer,
	Box,
	Text,
	Stack,
	Group,
	Badge,
	ScrollArea,
	Avatar,
	UnstyledButton,
	Divider,
} from "@mantine/core";
import { IconBuilding, IconCalendar, IconChevronRight, IconDroplet, IconEye, IconFlame, IconMap2, IconMapPin, IconShieldCheck, IconTrain, IconUser } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { UnifiedListing } from "@shared/api/types";
import { translateDistrict, translateRegion, normalizeLocationKey } from "@shared/lib/regions";
import { localizeMicrodistrict } from "@shared/constants/microdistricts";
import { useSwipeDismiss } from "@shared/hooks/useSwipeDismiss";
import { CommentsDrawer } from "./CommentsDrawer";
import { DrawerBackButton } from "./DrawerBackButton";
import { formatPrice, radii } from "@app/styles/theme";

interface DescriptionDrawerProps {
	opened: boolean;
	onClose: () => void;
	listing: UnifiedListing;
	onCommentAdded?: () => void;
	/** Close this drawer and open the map drawer instead (mutually exclusive). */
	onViewMap: () => void;
	container?: HTMLElement | null;
}

// Apartment/house amenity codes → seller-namespace i18n keys.
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

// Nearby amenity codes → seller-namespace keys.
const NEARBY_I18N: Record<string, string> = {
	hospital: "createListing.nearHospital",
	playground: "createListing.nearPlayground",
	kindergarten: "createListing.nearKindergarten",
	bus_stop: "createListing.nearBus",
	park: "createListing.nearPark",
	entertainment: "createListing.nearEntertainment",
	restaurant: "createListing.nearRestaurant",
	parking: "createListing.nearParking",
	supermarket: "createListing.nearSupermarket",
	school: "createListing.nearSchool",
};

// Enum value → seller-namespace key for single-value enum fields.
const ENUM_VALUES: Record<string, Record<string, string>> = {
	condition: {
		euro: "createListing.condEuro",
		cosmetic: "createListing.condCosmetic",
		needs_repair: "createListing.condRepair",
		rough: "createListing.condRough",
		none: "createListing.condNone",
		shell: "createListing.condShell",
		medium: "createListing.condMedium",
		designer: "createListing.condDesigner",
		turnkey: "createListing.condTurnkey",
		needs_repair_comm: "createListing.condNeedsRepairComm",
	},
	market_type: {
		new: "createListing.marketTypeNew",
		secondary: "createListing.marketTypeSecondary",
	},
	wall_material: {
		brick: "createListing.wallMaterialBrick",
		gasblock: "createListing.wallMaterialGasblock",
		panel: "createListing.wallMaterialPanel",
		monolith: "createListing.wallMaterialMonolith",
		other: "createListing.wallMaterialOther",
	},
	furniture: {
		none: "createListing.furnitureNone",
		partial: "createListing.furniturePartial",
		full: "createListing.furnitureFull",
		built_in: "createListing.furnitureBuiltIn",
	},
	balcony: {
		none: "createListing.balconyNone",
		balcony: "createListing.balconyBalcony",
		loggia: "createListing.balconyLoggia",
		terrace: "createListing.balconyTerrace",
	},
	listing_subtype: {
		standard: "createListing.listingSubtypeStandard",
		studio: "createListing.listingSubtypeStudio",
		free_plan: "createListing.listingSubtypeFreePlan",
	},
	house_type: {
		cottage: "createListing.htCottage",
		townhouse: "createListing.htTownhouse",
		country_house: "createListing.htCountry",
		dacha: "createListing.htDacha",
		part: "createListing.htPart",
	},
	land_shape: {
		rectangular: "createListing.landShapeRectangular",
		irregular: "createListing.landShapeIrregular",
	},
	electricity: {
		yes: "createListing.yes",
		no: "createListing.no",
		possible: "createListing.possible",
	},
	gas_supply: {
		yes: "createListing.yes",
		no: "createListing.no",
		possible: "createListing.possible",
	},
	sewage: {
		central: "createListing.sewCentral",
		septic: "createListing.sewSeptic",
		none: "createListing.sewNone",
	},
	entrance: {
		separate: "createListing.entranceSeparate",
		yard: "createListing.entranceYard",
		street: "createListing.entranceStreet",
		mall: "createListing.entranceMall",
	},
	building_class: {
		standalone: "createListing.buildingClassStandalone",
		embedded: "createListing.buildingClassEmbedded",
		business_center: "createListing.buildingClassBusinessCenter",
		mall: "createListing.buildingClassMall",
	},
	commercial_type: {
		office: "createListing.commercialTypeOffice",
		shop: "createListing.commercialTypeShop",
		warehouse: "createListing.commercialTypeWarehouse",
		production: "createListing.commercialTypeProduction",
		restaurant: "createListing.commercialTypeRestaurant",
		hotel: "createListing.commercialTypeHotel",
		other: "createListing.commercialTypeOther",
	},
};

// Array-value fields: each element maps to a seller-namespace key.
const ARRAY_ENUM_VALUES: Record<string, Record<string, string>> = {
	water_supply: {
		in_house: "createListing.wsInHouse",
		central: "createListing.wsCentral",
		possible: "createListing.wsPossible",
		well: "createListing.wsWell",
		border: "createListing.wsBorder",
		borehole: "createListing.wsBorehole",
		none: "createListing.wsNone",
	},
	heating: {
		central: "createListing.heatCentral",
		gas: "createListing.heatGas",
		solid: "createListing.heatSolid",
		liquid: "createListing.heatLiquid",
		electric: "createListing.heatElectric",
		mixed: "createListing.heatMixed",
		none: "createListing.heatNone",
	},
	house_condition: {
		designer: "createListing.hcDesigner",
		medium: "createListing.hcMedium",
		euro: "createListing.hcEuro",
		repair: "createListing.hcRepair",
		pre_finish: "createListing.hcPreFinish",
		unfinished: "createListing.hcUnfinished",
		rough: "createListing.hcRough",
		demolish: "createListing.hcDemolish",
	},
	location_type: {
		city: "createListing.locCity",
		suburb: "createListing.locSuburb",
		rural: "createListing.locRural",
		highway: "createListing.locHighway",
		water: "createListing.locWater",
		foothills: "createListing.locFoothills",
		dacha: "createListing.locDacha",
		gated: "createListing.locGated",
	},
};

export const DescriptionDrawer: FC<DescriptionDrawerProps> = ({
	opened,
	onClose,
	listing,
	onCommentAdded,
	onViewMap,
	container,
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

	// Locale-driven section markers strip crawler-injected structured blocks.
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

	// Helpers for seller-namespace translations with raw-value fallback.
	const ts = (key: string, fallback?: string) =>
		t(key, { ns: "seller", defaultValue: fallback ?? key });

	const enumVal = (field: string, value: string | null | undefined) => {
		if (!value) return null;
		const map = ENUM_VALUES[field];
		return map?.[value] ? ts(map[value], value) : value;
	};

	const arrayVals = (field: string, values: string[] | null | undefined): string[] => {
		if (!values?.length) return [];
		const map = ARRAY_ENUM_VALUES[field];
		return values.map((v) => (map?.[v] ? ts(map[v], v) : v));
	};

	const amenityLabel = (a: string) => {
		const key = AMENITY_I18N[a];
		return key ? ts(key, a) : a;
	};
	const nearbyLabel = (a: string) => {
		const key = NEARBY_I18N[a];
		return key ? ts(key, a) : a;
	};

	// ── All params as unified chips: rooms / floor / areas / ceiling / price-per-sqm ──
	type ParamChip = { value: string; label: string };
	const paramChips: ParamChip[] = [];
	if (listing.rooms)
		paramChips.push({ value: String(listing.rooms), label: t("listing.rooms") });
	if (listing.floor)
		paramChips.push({ value: `${listing.floor}/${listing.total_floors || "?"}`, label: t("listing.floorLabel") });
	if (listing.area)
		paramChips.push({ value: `${listing.area} м²`, label: t("descriptionDrawer.areaTotal", "общая") });
	if (listing.living_area)
		paramChips.push({ value: `${listing.living_area} м²`, label: t("descriptionDrawer.livingArea", "жилая") });
	if (listing.kitchen_area)
		paramChips.push({ value: `${listing.kitchen_area} м²`, label: t("descriptionDrawer.kitchenArea", "кухня") });
	if (listing.ceiling_height)
		paramChips.push({ value: `${listing.ceiling_height} м`, label: t("descriptionDrawer.ceilingHeight") });
	if (listing.land_area)
		paramChips.push({ value: `${listing.land_area}`, label: t("descriptionDrawer.landArea", "сот.") });
	if (listing.price_per_sqm)
		paramChips.push({ value: formatPrice(listing.price_per_sqm, listing.currency), label: t("descriptionDrawer.pricePerSqm", "за м²") });

	// ── Location: one-line region/city/district dedup ────────────────────────
	// Normalize both region and city to their canonical keys before comparing,
	// so "tashkent_city" and "Tashkent" both resolve to "toshkent_shahri".
	const normalizedRegionKey = normalizeLocationKey(listing.region, 'region');
	const normalizedCityKey = normalizeLocationKey(listing.city, 'region');
	const translatedRegion = listing.region ? translateRegion(listing.region, t) : "";
	const showCity = Boolean(listing.city) &&
		normalizedCityKey !== normalizedRegionKey &&
		listing.city!.toLowerCase() !== translatedRegion.toLowerCase();
	const locationLine = [
		listing.region ? translateRegion(listing.region, t) : null,
		showCity && listing.city ? listing.city : null,
		listing.district ? translateDistrict(listing.district, t) : null,
		listing.microdistrict
			? localizeMicrodistrict(listing.microdistrict, i18n.language)
			: null,
	]
		.filter(Boolean)
		.join(", ");


	// ── Characteristic rows: labeled key-value pairs ─────────────────────────
	const yes = t("descriptionDrawer.yes", "Есть");
	type CharRow = { label: string; value: string };
	const characteristicRows: CharRow[] = [
		{ label: t("card.propertyType.title", "Тип"), value: propertyLabel },
	];
	if (listing.building_type)
		characteristicRows.push({
			label: ts("createListing.buildingType", "Тип строения"),
			value: t(`listing.buildingType.${listing.building_type}`, listing.building_type),
		});
	const marketVal = enumVal("market_type", listing.market_type);
	if (marketVal)
		characteristicRows.push({ label: ts("createListing.marketTypeLabel", "Тип рынка"), value: marketVal });
	const conditionVal = enumVal("condition", listing.condition);
	if (conditionVal)
		characteristicRows.push({ label: ts("createListing.condition", "Ремонт"), value: conditionVal });
	const houseTypeVal = enumVal("house_type", listing.house_type);
	if (houseTypeVal)
		characteristicRows.push({ label: ts("createListing.houseType", "Тип дома"), value: houseTypeVal });
	const houseCondVals = arrayVals("house_condition", listing.house_condition);
	if (houseCondVals.length)
		characteristicRows.push({ label: ts("createListing.houseCondition", "Состояние дома"), value: houseCondVals.join(", ") });
	const locationTypeVals = arrayVals("location_type", listing.location_type);
	if (locationTypeVals.length)
		characteristicRows.push({ label: ts("createListing.locationType", "Расположение"), value: locationTypeVals.join(", ") });
	const wallVal = enumVal("wall_material", listing.wall_material);
	if (wallVal)
		characteristicRows.push({ label: ts("createListing.wallMaterialLabel", "Материал стен"), value: wallVal });
	const furnitureVal = enumVal("furniture", listing.furniture);
	if (furnitureVal)
		characteristicRows.push({ label: ts("createListing.furnitureLabel", "Мебель"), value: furnitureVal });
	const subtypeVal = enumVal("listing_subtype", listing.listing_subtype);
	if (subtypeVal)
		characteristicRows.push({ label: ts("createListing.listingSubtypeLabel", "Планировка"), value: subtypeVal });
	if (listing.balcony && listing.balcony !== "none") {
		const balconyVal = enumVal("balcony", listing.balcony);
		if (balconyVal)
			characteristicRows.push({ label: ts("createListing.balconyLabel", "Балкон"), value: balconyVal });
	}
	const landShapeVal = enumVal("land_shape", listing.land_shape);
	if (landShapeVal)
		characteristicRows.push({ label: ts("createListing.landShapeLabel", "Форма участка"), value: landShapeVal });
	const commercialVal = enumVal("commercial_type", listing.commercial_type);
	if (commercialVal)
		characteristicRows.push({ label: ts("createListing.commercialTypeLabel", "Тип помещения"), value: commercialVal });
	const buildingClassVal = enumVal("building_class", listing.building_class);
	if (buildingClassVal)
		characteristicRows.push({ label: ts("createListing.buildingClassLabel", "Класс здания"), value: buildingClassVal });
	const entranceVal = enumVal("entrance", listing.entrance);
	if (entranceVal)
		characteristicRows.push({ label: ts("createListing.entranceLabel", "Вход"), value: entranceVal });
	if (listing.parking_comm)
		characteristicRows.push({ label: ts("createListing.parkingCommLabel", "Парковка"), value: yes });
	if (listing.garage)
		characteristicRows.push({ label: ts("createListing.garageLabel", "Гараж"), value: yes });
	if (listing.basement)
		characteristicRows.push({ label: ts("createListing.basementLabel", "Подвал"), value: yes });
	if (listing.buildings_exist)
		characteristicRows.push({ label: ts("createListing.buildingsExistLabel", "Постройки"), value: yes });
	if (listing.fence)
		characteristicRows.push({ label: ts("createListing.fenceLabel", "Ограждение"), value: yes });

	// Utilities section.
	const hasUtilities =
		(listing.water_supply?.length ?? 0) > 0 ||
		listing.electricity ||
		(listing.heating?.length ?? 0) > 0 ||
		listing.gas_supply ||
		listing.sewage;

	const waterLabel = ts("createListing.waterSupply");
	const heatLabel = ts("createListing.heating");
	const elecLabel = ts("createListing.electricity");
	const gasLabel = ts("createListing.gasSupply");
	const sewageLabel = ts("createListing.sewage");

	const utilityItems: Array<{ icon: typeof IconDroplet | null; label: string }> = [
		...arrayVals("water_supply", listing.water_supply).map((v) => ({
			icon: IconDroplet as typeof IconDroplet,
			label: `${waterLabel}: ${v}`,
		})),
		...(listing.electricity
			? [{ icon: null, label: `${elecLabel}: ${enumVal("electricity", listing.electricity)}` }]
			: []),
		...arrayVals("heating", listing.heating).map((v) => ({
			icon: IconFlame as typeof IconDroplet,
			label: `${heatLabel}: ${v}`,
		})),
		...(listing.gas_supply
			? [{ icon: null, label: `${gasLabel}: ${enumVal("gas_supply", listing.gas_supply)}` }]
			: []),
		...(listing.sewage
			? [{ icon: null, label: `${sewageLabel}: ${enumVal("sewage", listing.sewage)}` }]
			: []),
	];

	// Exclude "balcony" from amenities if it's already captured as a balcony-type characteristic.
	const amenities = (listing.amenities ?? []).filter(
		(a) => !(a === "balcony" && listing.balcony && listing.balcony !== "none"),
	);
	const nearbyAmenities = listing.nearby_amenities ?? [];

	const hasSeller = Boolean(
		listing.seller_id && (listing.seller_name || listing.seller_avatar_url),
	);
	const publishedAt = new Date(listing.created_at).toLocaleDateString(
		i18n.language?.startsWith("uz") ? "uz-Latn" : "ru-RU",
		{ day: "numeric", month: "long", year: "numeric" },
	);

	const hasFinance =
		listing.mortgage_ok ||
		listing.installment_ok ||
		listing.halol_ok ||
		listing.deed_type;

	const hasRent =
		listing.type === "rent" &&
		(listing.rent_period ||
			listing.deposit != null ||
			listing.utilities_incl != null ||
			listing.min_rent_months != null ||
			listing.allowed_students != null ||
			listing.allowed_pets != null ||
			(listing.rent_payment?.length ?? 0) > 0);

	return (
		<>
			<Drawer
				opened={opened}
				onClose={onClose}
				position="bottom"
				size="90%"
				withCloseButton={false}
				zIndex={10001}
				portalProps={container ? { target: container } : undefined}
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
						position: "relative",
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
					<ScrollArea style={{ flex: 1 }} px="md" py="sm" viewportRef={scrollRef} viewportProps={{ style: { paddingBottom: 80 } }}>
						<Stack gap="md">
							{/* Price hero + deal type */}
							<Group justify="space-between" align="flex-start" wrap="nowrap">
								<Box>
									<Text fw={800} style={{ fontSize: 26, lineHeight: 1.1 }}>
										{formattedPrice}
									</Text>
									{listing.is_negotiable && (
										<Text size="xs" c="green.7" fw={500}>
											{t("descriptionDrawer.negotiable")}
										</Text>
									)}
								</Box>
								<Group gap={6}>
									{listing.urgent_flag && (
										<Badge size="sm" variant="filled" color="red" radius="sm">
											{t("listing.badges.urgent")}
										</Badge>
									)}
									<Badge
										size="lg"
										variant="light"
										radius="sm"
										color={listing.type === "sell" ? "blue" : "green"}
									>
										{dealLabel}
									</Badge>
								</Group>
							</Group>

							{listing.title && (
								<Text fw={600} size="md">
									{listing.title}
								</Text>
							)}

							{/* Unified params chips: rooms / areas / floor / ceiling / price-per-sqm */}
							{paramChips.length > 0 && (
								<Group gap={8} wrap="wrap">
									{paramChips.map((chip, i) => (
										<Box
											key={i}
											px={12}
											py={6}
											style={{
												border: "1px solid var(--mantine-color-gray-3)",
												borderRadius: 10,
												background: "var(--mantine-color-gray-0)",
												textAlign: "center",
												minWidth: 56,
											}}
										>
											<Text fw={700} size="md" lh={1.2}>
												{chip.value}
											</Text>
											<Text size="10px" c="dimmed" lh={1.2}>
												{chip.label}
											</Text>
										</Box>
									))}
								</Group>
							)}

							{/* Characteristics: labeled key-value grid */}
							{characteristicRows.length > 0 && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.characteristics")}
									</Text>
									<Box
										style={{
											display: "grid",
											gridTemplateColumns: "auto 1fr",
											columnGap: 12,
											rowGap: 5,
										}}
									>
										{characteristicRows.map((row) => (
											<Fragment key={row.label}>
												<Text size="sm" c="dimmed" style={{ whiteSpace: "nowrap" }}>
													{row.label}
												</Text>
												<Text size="sm" fw={500}>
													{row.value}
												</Text>
											</Fragment>
										))}
									</Box>
								</Stack>
							)}

							{/* Sale finance section */}
							{hasFinance && listing.type === "sell" && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.finance")}
									</Text>
									<Group gap={6}>
										{listing.mortgage_ok && (
											<Badge size="sm" variant="filled" color="teal" radius="sm">
												{t("listing.badges.mortgage")}
											</Badge>
										)}
										{listing.installment_ok && (
											<Badge size="sm" variant="filled" color="teal" radius="sm">
												{t("listing.badges.installment")}
											</Badge>
										)}
										{listing.halol_ok && (
											<Badge size="sm" variant="filled" color="teal" radius="sm">
												{t("listing.badges.halol")}
											</Badge>
										)}
										{listing.deed_type && (
											<Badge size="sm" variant="outline" color="gray" radius="sm">
												{t(
													`descriptionDrawer.deed.${listing.deed_type}`,
													listing.deed_type,
												)}
											</Badge>
										)}
									</Group>
								</Stack>
							)}

							{/* Rent conditions */}
							{hasRent && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.rentConditions")}
									</Text>
									<Group gap={6}>
										{listing.rent_period && (
											<Badge size="sm" variant="light" color="blue" radius="sm">
												{t(
													`descriptionDrawer.rentPeriod.${listing.rent_period}`,
													listing.rent_period,
												)}
											</Badge>
										)}
										{listing.deposit != null && (
											<Badge size="sm" variant="outline" color="gray" radius="sm">
												{t("descriptionDrawer.deposit")}:{" "}
												{formatPrice(listing.deposit, listing.currency)}
											</Badge>
										)}
										{listing.utilities_incl === true && (
											<Badge size="sm" variant="light" color="green" radius="sm">
												{t("descriptionDrawer.utilitiesIncl")}
											</Badge>
										)}
										{listing.min_rent_months != null && (
											<Badge size="sm" variant="outline" color="gray" radius="sm">
												{t("descriptionDrawer.minRentMonths")}: {listing.min_rent_months}{" "}
												{t("descriptionDrawer.months")}
											</Badge>
										)}
										{listing.allowed_students === true && (
											<Badge size="sm" variant="light" color="violet" radius="sm">
												✓ {t("descriptionDrawer.allowedStudents")}
											</Badge>
										)}
										{listing.allowed_students === false && (
											<Badge size="sm" variant="light" color="red" radius="sm">
												✗ {t("descriptionDrawer.allowedStudents")}
											</Badge>
										)}
										{listing.allowed_pets === true && (
											<Badge size="sm" variant="light" color="violet" radius="sm">
												✓ {t("descriptionDrawer.allowedPets")}
											</Badge>
										)}
										{listing.allowed_pets === false && (
											<Badge size="sm" variant="light" color="red" radius="sm">
												✗ {t("descriptionDrawer.allowedPets")}
											</Badge>
										)}
										{listing.rent_payment?.map((v) => (
											<Badge key={v} size="sm" variant="outline" color="gray" radius="sm">
												{v}
											</Badge>
										))}
									</Group>
								</Stack>
							)}

							{/* Utilities / infrastructure */}
							{hasUtilities && utilityItems.length > 0 && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.utilities")}
									</Text>
									<Group gap={6}>
										{utilityItems.map((item) => (
											<Badge
												key={item.label}
												size="sm"
												variant="outline"
												color="gray"
												radius="sm"
											>
												{item.label}
											</Badge>
										))}
									</Group>
								</Stack>
							)}

							{/* Amenities */}
							{amenities.length > 0 && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.amenities")}
									</Text>
									<Group gap={6}>
										{amenities.map((a) => (
											<Badge key={a} size="sm" variant="outline" color="gray" radius="sm">
												{amenityLabel(a)}
											</Badge>
										))}
									</Group>
								</Stack>
							)}

							{/* Nearby */}
							{nearbyAmenities.length > 0 && (
								<Stack gap={6}>
									<Text fw={600} size="xs" c="dimmed" tt="uppercase">
										{t("descriptionDrawer.nearby")}
									</Text>
									<Group gap={6}>
										{nearbyAmenities.map((a) => (
											<Badge
												key={a}
												size="sm"
												variant="outline"
												color="teal"
												radius="sm"
											>
												{nearbyLabel(a)}
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
							{(listing.region ||
								listing.city ||
								listing.jk_name ||
								listing.metro_station ||
								listing.microdistrict ||
								listing.landmark ||
								listing.district ||
								listing.latitude) && (
								<Stack gap={4}>
									{/* Region / city / district — one combined line */}
									{locationLine && (
										<Group gap={6} wrap="nowrap">
											<IconMapPin
												size={14}
												color="var(--mantine-color-gray-6)"
												style={{ flexShrink: 0 }}
											/>
											<Text size="sm" c="dimmed">
												{locationLine}
											</Text>
										</Group>
									)}
									{/* JK name */}
									{listing.jk_name && (
										<Group gap={6} wrap="nowrap">
											<IconBuilding
												size={14}
												color="var(--mantine-color-gray-6)"
												style={{ flexShrink: 0 }}
											/>
											<Text size="sm" c="dimmed">
												{t("descriptionDrawer.location.jk")}: {listing.jk_name}
											</Text>
										</Group>
									)}
									{/* Metro — translated via seller i18n keys */}
									{listing.metro_station && (
										<Group gap={6} wrap="nowrap">
											<IconTrain
												size={14}
												color="var(--mantine-color-grape-6)"
												style={{ flexShrink: 0 }}
											/>
											<Text size="sm" c="dimmed">
												{t("descriptionDrawer.location.metro")}:{" "}
												{ts(
													`createListing.metroStation.${listing.metro_station}`,
													listing.metro_station
														.replace(/_/g, " ")
														.replace(/^\w/, (c) => c.toUpperCase()),
												)}
											</Text>
										</Group>
									)}
									{/* Landmark */}
									{listing.landmark && (
										<Group gap={6} wrap="nowrap">
											<IconMapPin
												size={14}
												color="var(--mantine-color-gray-5)"
												style={{ flexShrink: 0 }}
											/>
											<Text size="sm" c="dimmed" fs="italic">
												{t("descriptionDrawer.location.landmark")}:{" "}
												{listing.landmark}
											</Text>
										</Group>
									)}
									{/* Map button — replaces raw address text */}
									{listing.latitude && listing.longitude && (
										<UnstyledButton
											mt={4}
											onClick={onViewMap}
											style={{
												display: "inline-flex",
												alignItems: "center",
												gap: 6,
												color: "var(--mantine-color-blue-6)",
												fontSize: "var(--mantine-font-size-sm)",
											}}
										>
											<IconMap2 size={14} />
											{t("descriptionDrawer.location.viewOnMap", "Посмотреть на карте")}
											<IconChevronRight size={12} />
										</UnstyledButton>
									)}
								</Stack>
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
												{listing.seller_type
													? t(`descriptionDrawer.sellerType.${listing.seller_type}`, listing.seller_type)
													: t("descriptionDrawer.seller")}
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
				</Box>
			</Drawer>

			<DrawerBackButton opened={opened} onClose={onClose} container={container} />

			<CommentsDrawer
				opened={commentsOpen}
				onClose={() => setCommentsOpen(false)}
				listingId={listing.id}
				onCommentAdded={onCommentAdded}
			/>
		</>
	);
};
