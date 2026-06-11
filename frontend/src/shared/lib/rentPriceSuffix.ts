/**
 * i18n key (buyer namespace) for the period suffix rendered after a rent
 * price: «/мес» for long-term, «/сутки» for daily housing, «/день» for
 * daily commercial. Land rents long-term only, so it resolves to «/мес».
 * Callers gate on `type === "rent"` themselves — sales show no suffix.
 */
export function rentPriceSuffixKey(
	rentPeriod?: string | null,
	propertyType?: string | null,
): "common.perMonth" | "common.perDay" | "common.perDayCommercial" {
	if (rentPeriod === "daily") {
		return propertyType === "commercial"
			? "common.perDayCommercial"
			: "common.perDay";
	}
	return "common.perMonth";
}
