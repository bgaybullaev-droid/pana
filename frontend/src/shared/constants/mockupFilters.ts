export const getConditionOpts = (t: any) => [
	{ value: "designer", label: t("seller:createListing.hcDesigner") },
	{ value: "euro", label: t("seller:createListing.condEuro") },
	{ value: "cosmetic", label: t("seller:createListing.condCosmetic") },
	{ value: "medium_repair", label: t("seller:createListing.hcMedium") },
	{ value: "needs_repair", label: t("seller:createListing.condRepair") },
	{ value: "rough", label: t("seller:createListing.condRough") },
	{ value: "pre_finish", label: t("seller:createListing.hcPreFinish") },
];

export const getBuildingTypeOpts = (t: any) => [
	{ value: "new", label: t("seller:createListing.buildingNew") },
	{ value: "secondary", label: t("seller:createListing.buildingSecondary") },
];

export const getHouseTypeOpts = (t: any) => [
	{ value: "cottage", label: t("seller:createListing.htCottage") },
	{ value: "townhouse", label: t("seller:createListing.htTownhouse") },
	{ value: "country_house", label: t("seller:createListing.htCountry") },
	{ value: "dacha", label: t("seller:createListing.htDacha") },
	{ value: "part_of_house", label: t("seller:createListing.htPart") },
];

export const getFurnishedOpts = (t: any) => [
	{ value: "yes", label: t("seller:createListing.yes") },
	{ value: "no", label: t("seller:createListing.no") },
];

export const getAptAmenityOpts = (t: any) => [
	{ value: "internet", label: t("seller:createListing.amenInternet") },
	{ value: "phone", label: t("seller:createListing.amenPhone") },
	{ value: "fridge", label: t("seller:createListing.amenFridge") },
	{ value: "tv", label: t("seller:createListing.amenTv") },
	{ value: "ac", label: t("seller:createListing.amenAc") },
	{ value: "cable_tv", label: t("seller:createListing.amenCable") },
	{ value: "washing_machine", label: t("seller:createListing.amenWashing") },
	{ value: "kitchen_set", label: t("seller:createListing.amenKitchen") },
];

export const getHouseAmenityOpts = (t: any) => [
	{ value: "pool", label: t("seller:createListing.amenPool") },
	{ value: "garage", label: t("seller:createListing.amenGarage") },
	{ value: "appliances", label: t("seller:createListing.amenAppliances") },
	{ value: "sewage", label: t("seller:createListing.amenSewage") },
	{ value: "garden", label: t("seller:createListing.amenGarden") },
	{ value: "security", label: t("seller:createListing.amenSecurity") },
	{ value: "basement", label: t("seller:createListing.amenBasement") },
	{ value: "sauna", label: t("seller:createListing.amenSauna") },
	{ value: "gym", label: t("seller:createListing.amenGym") },
];

export const getWaterSupplyOpts = (t: any) => [
	{ value: "in_house", label: t("seller:createListing.wsInHouse") },
	{ value: "central", label: t("seller:createListing.wsCentral") },
	{ value: "well", label: t("seller:createListing.wsWell") },
	{ value: "borehole", label: t("seller:createListing.wsBorehole") },
];
