import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import dayjs from "dayjs";
import "dayjs/locale/ru";
import "dayjs/locale/uz-latn";

import ruAdmin from "./locales/ru/admin.json";
import uzAdmin from "./locales/uz/admin.json";
import uzCyrlAdmin from "./locales/uz-cyrl/admin.json";
import uzLatnAdmin from "./locales/uz-latn/admin.json";
import ruBuyer from "./locales/ru/buyer.json";
import uzBuyer from "./locales/uz/buyer.json";
import uzCyrlBuyer from "./locales/uz-cyrl/buyer.json";
import uzLatnBuyer from "./locales/uz-latn/buyer.json";
import ruSeller from "./locales/ru/seller.json";
import uzSeller from "./locales/uz/seller.json";
import uzCyrlSeller from "./locales/uz-cyrl/seller.json";
import uzLatnSeller from "./locales/uz-latn/seller.json";
import ruCommon from "./locales/ru/common.json";
import uzCommon from "./locales/uz/common.json";
import uzCyrlCommon from "./locales/uz-cyrl/common.json";
import uzLatnCommon from "./locales/uz-latn/common.json";

export const SUPPORTED_LOCALES = ["ru", "uz", "uz-cyrl", "uz-latn"] as const;

const savedLang = localStorage.getItem("i18nextLng") || "ru";

i18n.use(initReactI18next).init({
	resources: {
		ru: { admin: ruAdmin, buyer: ruBuyer, seller: ruSeller, common: ruCommon },
		uz: { admin: uzAdmin, buyer: uzBuyer, seller: uzSeller, common: uzCommon },
		"uz-cyrl": {
			admin: uzCyrlAdmin,
			buyer: uzCyrlBuyer,
			seller: uzCyrlSeller,
			common: uzCyrlCommon,
		},
		"uz-latn": {
			admin: uzLatnAdmin,
			buyer: uzLatnBuyer,
			seller: uzLatnSeller,
			common: uzLatnCommon,
		},
	},
	lng: savedLang,
	fallbackLng: "ru",
	supportedLngs: SUPPORTED_LOCALES as unknown as string[],
	ns: ["admin", "buyer", "seller", "common"],
	defaultNS: "common",
	interpolation: { escapeValue: false },
	pluralSeparator: "_",
	// i18next normalises BCP-47 codes by default — for a 2-part code
	// like ``uz-cyrl`` ``formatLanguageCode`` uppercases the region to
	// ``uz-CYRL``, which then fails the lookup against our lowercase
	// ``supportedLngs`` entry and falls back to bare ``uz`` (Latin).
	// ``lowerCaseLng: true`` keeps the code as-authored so the lookup
	// chain stays exactly ``[uz-cyrl, uz, ru]``.
	lowerCaseLng: true,
});

// Sync dayjs locale
function syncDayjs(lng: string) {
	if (lng === "ru") dayjs.locale("ru");
	else dayjs.locale("uz-latn"); // both uz and uz-cyrl use uz-latn date format
}

syncDayjs(savedLang);

// DIAGNOSTIC: expose i18n on window for Playwright. Safe to keep — only
// referenced from tests; production minifier drops the global if nothing
// reads it. Remove after the uz-cyrl bug is fixed.
if (typeof window !== "undefined") {
	(window as unknown as { __i18n: unknown }).__i18n = i18n;
}

// Callbacks that fire when content language changes (for re-fetching listing data)
const _contentLangCallbacks: Array<() => void> = [];
export function onContentLanguageChanged(cb: () => void) {
	_contentLangCallbacks.push(cb);
	return () => {
		const idx = _contentLangCallbacks.indexOf(cb);
		if (idx >= 0) _contentLangCallbacks.splice(idx, 1);
	};
}

i18n.on("languageChanged", (lng) => {
	localStorage.setItem("i18nextLng", lng);
	syncDayjs(lng);
	// Notify listing stores to refetch content in the new language
	_contentLangCallbacks.forEach((cb) => cb());
});

// =============================================================================
// Block D D1 — backend ↔ frontend locale boundary
//
// The backend canonicalises Cyrillic Uzbek as "uz_cyrl" (Python-style
// snake_case). The frontend i18n folder is named "uz-cyrl" (kebab-case),
// matching BCP-47 conventions. Map at the API boundary so neither side
// has to know about the other's convention.
// =============================================================================

export type BackendLanguage = "ru" | "uz" | "uz_cyrl";
export type FrontendLocale = "ru" | "uz" | "uz-cyrl" | "uz-latn";

export function backendToFrontendLocale(lang: BackendLanguage | string): FrontendLocale {
	if (lang === "uz_cyrl" || lang === "uz-cyrl") return "uz-cyrl";
	if (lang === "uz-latn") return "uz-latn";
	if (lang === "uz") return "uz";
	return "ru";
}

export function frontendToBackendLanguage(locale: FrontendLocale | string): BackendLanguage {
	if (locale === "uz-cyrl" || locale === "uz_cyrl") return "uz_cyrl";
	// Backend has no dedicated "uz-latn" code — Latin-script Uzbek maps to "uz"
	// per the Block D contract. URL-path locale "uz-latn" is purely a frontend
	// concept distinguishing it from the ambiguous "uz".
	if (locale === "uz-latn" || locale === "uz") return "uz";
	return "ru";
}

export default i18n;
