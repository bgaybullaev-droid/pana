import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import dayjs from "dayjs";
import "dayjs/locale/ru";
import "dayjs/locale/uz-latn";

import ruAdmin from "./locales/ru/admin.json";
import uzAdmin from "./locales/uz/admin.json";
import ruBuyer from "./locales/ru/buyer.json";
import uzBuyer from "./locales/uz/buyer.json";
import ruSeller from "./locales/ru/seller.json";
import uzSeller from "./locales/uz/seller.json";
import ruCommon from "./locales/ru/common.json";
import uzCommon from "./locales/uz/common.json";

const savedLang = localStorage.getItem("i18nextLng") || "ru";

i18n.use(initReactI18next).init({
	resources: {
		ru: { admin: ruAdmin, buyer: ruBuyer, seller: ruSeller, common: ruCommon },
		uz: { admin: uzAdmin, buyer: uzBuyer, seller: uzSeller, common: uzCommon },
	},
	lng: savedLang,
	fallbackLng: "ru",
	ns: ["admin", "buyer", "seller", "common"],
	defaultNS: "common",
	interpolation: { escapeValue: false },
});

// Sync dayjs locale
function syncDayjs(lng: string) {
	dayjs.locale(lng === "uz" ? "uz-latn" : "ru");
}

syncDayjs(savedLang);

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

export default i18n;
