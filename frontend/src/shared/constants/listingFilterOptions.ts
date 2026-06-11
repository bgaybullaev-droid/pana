import type { TFunction } from "i18next";

/**
 * Canonical buyer-filter options.
 *
 * The `value`s MUST match what the seller form writes to the DB and the
 * backend CHECK constraint (see ListingFormFields `conditionOpts` and the
 * `ck_listings_condition_enum` migration). The look-alike list in
 * `mockupFilters.ts` uses different values (e.g. `medium_repair`,
 * `pre_finish`) that never match stored data — do not use it for filtering.
 */
export const getConditionFilterOpts = (t: TFunction) => [
	{ value: "euro", label: t("seller:createListing.condEuro") },
	{ value: "cosmetic", label: t("seller:createListing.condCosmetic") },
	{ value: "needs_repair", label: t("seller:createListing.condRepair") },
	{ value: "rough", label: t("seller:createListing.condRough") },
	{ value: "none", label: t("seller:createListing.condNone") },
	{ value: "shell", label: t("seller:createListing.condShell") },
	{ value: "medium", label: t("seller:createListing.condMedium") },
	{ value: "designer", label: t("seller:createListing.condDesigner") },
	{ value: "turnkey", label: t("seller:createListing.condTurnkey") },
	{
		value: "needs_repair_comm",
		label: t("seller:createListing.condNeedsRepairComm"),
	},
];

export const getBuildingTypeFilterOpts = (t: TFunction) => [
	{ value: "new" as const, label: t("seller:createListing.buildingNew") },
	{
		value: "secondary" as const,
		label: t("seller:createListing.buildingSecondary"),
	},
];
