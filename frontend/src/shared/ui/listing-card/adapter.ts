// T-020 — getListingCardContent: transform a listing into the view-data a
// card needs, WITHOUT any hard-coded (listing.type === 'rent') checks.
//
// All SHOW/HIDE decisions route through the visibility matrix via
// `getCardChipFields`, `getCardTagFields`, `getCardFinanceFields`. The
// consumer card component renders the arrays we return — it does not add
// further conditional branches.

import type { TFunction } from "i18next";
import type { ListingListItem } from "@shared/api/types";
import {
	isVisible,
	normalizeCombo,
	type DealType,
	type FieldKey,
	type PropertyType,
} from "@modules/seller/feature/listing-form/lib/visibility";
import { type PricePeriod } from "@app/styles/theme";
import {
	getCardChipFields,
	getCardFinanceFields,
	getCardTagFields,
} from "./listingCardConfig";

export interface CardChip {
	key: FieldKey;
	// Primary label rendered in the chip (e.g. "3 комн", "55 м²", "3/9").
	label: string;
}

export interface CardBadge {
	key: FieldKey;
	label: string;
}

export interface DealTypeBadge {
	// i18n key to render as the badge label.
	labelKey: string;
	// Background color token (RGBA string). Blue for sell, green for rent.
	bg: string;
}

// T-021 — status badges. Extensible: to add a new badge kind, append a
// new `type` string literal here and a new rule in `computeBadges()`.
// The UI is a pure renderer — it does not know about badge semantics.
export type CardStatusBadgeType = "verified" | "urgent";

export interface CardStatusBadge {
	type: CardStatusBadgeType;
	label: string;
}

export interface ListingCardContent {
	chips: CardChip[];
	tagLine: string | null;
	financeBadges: CardBadge[];
	badges: CardStatusBadge[];
	dealTypeBadge: DealTypeBadge;
	price: {
		amount: number;
		currency: string;
		period: PricePeriod;
	};
}

// Known enum value allowlists for tag labels. Unknown values (e.g. raw crawler
// strings) are SKIPPED rather than emitted as-is. Matches the previous
// behavior in ListingCard.tsx so we don't regress the UI.
const KNOWN_BUILDING_TYPES = new Set(["new", "secondary"]);
const KNOWN_CONDITIONS = new Set(["euro", "cosmetic", "needs_repair", "rough"]);
const KNOWN_LAND_PURPOSES = new Set(["private", "industrial"]);

function chipLabel(
	field: FieldKey,
	listing: ListingListItem,
	t: TFunction,
): string | null {
	switch (field) {
		case "rooms":
			return listing.rooms != null
				? `${listing.rooms} ${t("common.rooms")}`
				: null;
		case "area":
			return listing.area != null ? `${listing.area} ${t("common.sqm")}` : null;
		case "floor":
			return listing.floor != null
				? `${listing.floor}/${listing.total_floors ?? "?"}`
				: null;
		case "land_area":
			return listing.land_area != null
				? `${listing.land_area} ${t("common.sotka", "соток")}`
				: null;
		default:
			return null;
	}
}

function tagLabel(
	field: FieldKey,
	listing: ListingListItem,
	t: TFunction,
): string | null {
	switch (field) {
		case "building_type": {
			const v = listing.building_type;
			if (v && KNOWN_BUILDING_TYPES.has(v)) {
				return t(`listing.buildingType.${v}`);
			}
			return null;
		}
		case "condition": {
			const v = listing.condition;
			if (v && KNOWN_CONDITIONS.has(v)) {
				return t(`listing.condition.${v}`);
			}
			return null;
		}
		case "land_purpose": {
			const v = listing.land_purpose;
			if (v && KNOWN_LAND_PURPOSES.has(v)) {
				return t(`listing.landPurpose.${v}`);
			}
			return null;
		}
		default:
			return null;
	}
}

// T-021 — status-badge rules live HERE and only here. The UI never
// re-checks these flags. To add a new badge kind:
//   1. Extend `CardStatusBadgeType` with the new literal.
//   2. Append a rule below (order defines default render priority).
//   3. Add the i18n key under `listing.badges.<type>`.
function computeBadges(
	listing: ListingListItem,
	t: TFunction,
): CardStatusBadge[] {
	const out: CardStatusBadge[] = [];

	// URGENT — null is a valid DB state (column nullable); treat as off.
	if (listing.urgent_flag === true) {
		out.push({
			type: "urgent",
			label: t("listing.badges.urgent", "Срочно"),
		});
	}

	// VERIFIED — sourced from the joined seller, may be null for
	// crawler-parsed listings that have no claimed seller.
	if (listing.is_verified === true) {
		out.push({
			type: "verified",
			label: t("listing.badges.verified", "Проверенный"),
		});
	}

	return out;
}

function financeLabel(
	field: FieldKey,
	listing: ListingListItem,
	t: TFunction,
): string | null {
	// Matrix-gated: caller already guarantees `field` is visible. We only
	// emit a badge when the flag itself is TRUE.
	if (field === "mortgage_ok" && listing.mortgage_ok)
		return t("listing.badges.mortgage", "Ипотека");
	if (field === "installment_ok" && listing.installment_ok)
		return t("listing.badges.installment", "Рассрочка");
	if (field === "halol_ok" && listing.halol_ok)
		return t("listing.badges.halol", "Халол");
	return null;
}

/**
 * Transform a listing into the card's view data. Pure function; no React
 * imports. The card component renders the returned arrays verbatim — it
 * must NOT add further conditional branches on `listing.type` or
 * `listing.property_type`.
 */
export function getListingCardContent(
	listing: ListingListItem,
	t: TFunction,
): ListingCardContent {
	const norm = normalizeCombo(
		listing.property_type as PropertyType,
		listing.type as DealType,
	);
	const chipFields = getCardChipFields(norm.propertyType, norm.dealType);
	const tagFields = getCardTagFields(norm.propertyType, norm.dealType);
	const financeFields = getCardFinanceFields(norm.propertyType, norm.dealType);

	// Price-period decision: ask the matrix directly whether `rent_period`
	// is visible for this combo. This is NOT a `listing.type === 'rent'`
	// branch — it's a matrix lookup that also respects rule P3 (land×rent
	// normalizes to land×sell).
	const period: PricePeriod = !isVisible(
		"rent_period",
		norm.propertyType,
		norm.dealType,
	)
		? "total"
		: listing.rent_period === "daily"
			? "day"
			: "month";

	const chips: CardChip[] = [];
	for (const f of chipFields) {
		const label = chipLabel(f, listing, t);
		if (label) chips.push({ key: f, label });
	}

	const tagParts: string[] = [];
	for (const f of tagFields) {
		const label = tagLabel(f, listing, t);
		if (label) tagParts.push(label);
	}
	const tagLine = tagParts.length > 0 ? tagParts.join(", ") : null;

	const financeBadges: CardBadge[] = [];
	for (const f of financeFields) {
		const label = financeLabel(f, listing, t);
		if (label) financeBadges.push({ key: f, label });
	}

	// Deal-type badge: label + color are OWNED by the type field itself,
	// not a field-visibility decision. Adapter returns both so the card
	// doesn't branch at render time.
	const dealTypeBadge: DealTypeBadge =
		norm.dealType === "sell"
			? { labelKey: "common.sell", bg: "rgba(34,139,230,0.9)" }
			: { labelKey: "common.rent", bg: "rgba(64,192,87,0.9)" };

	return {
		chips,
		tagLine,
		financeBadges,
		badges: computeBadges(listing, t),
		dealTypeBadge,
		price: {
			amount: listing.price,
			currency: listing.currency,
			period,
		},
	};
}
