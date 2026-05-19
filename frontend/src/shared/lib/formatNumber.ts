import i18n from "@shared/i18n";

const LOCALE_MAP: Record<string, string> = {
	ru: "ru-RU",
	uz: "uz-Latn-UZ",
	"uz-latn": "uz-Latn-UZ",
	"uz-cyrl": "uz-Cyrl-UZ",
};

function localeFor(): string {
	return LOCALE_MAP[i18n.language] || "uz-UZ";
}

export function formatNumber(value: number): string {
	return value.toLocaleString(localeFor());
}

export function formatPrice(value: number, currency: string): string {
	return `${formatNumber(value)} ${currency}`;
}

export function formatCount(
	value: number,
	keyBase: string,
	ns?: string,
): string {
	return i18n.t(keyBase, { count: value, ns });
}
