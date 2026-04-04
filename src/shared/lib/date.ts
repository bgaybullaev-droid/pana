/**
 * Date utilities for UTC+05:00 (Asia/Tashkent) timezone
 * Locale-aware: reads current language from i18next
 */

import i18n from "i18next";

const TIMEZONE = "Asia/Tashkent";
const TIMEZONE_LABEL = "UTC+5";

/** Map i18n language code to Intl locale */
function getLocale(): string {
	return i18n.language === "uz" ? "uz-Latn" : "ru-RU";
}

/**
 * Get current time in UTC+05:00
 */
export const getNow = (): Date => {
	return new Date();
};

/**
 * Parse ISO date string and return Date object
 * The server returns UTC timestamps, this converts them properly
 */
export const parseDate = (dateString: string): Date => {
	return new Date(dateString);
};

/**
 * Format relative time ago (locale-aware)
 */
export const formatTimeAgo = (dateString: string): string => {
	const date = parseDate(dateString);
	const now = getNow();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMins / 60);
	const diffDays = Math.floor(diffHours / 24);

	const isUz = i18n.language === "uz";

	if (diffMins < 1) return isUz ? "hozirgina" : "только что";
	if (diffMins < 60) return isUz ? `${diffMins} daq` : `${diffMins} мин`;
	if (diffHours < 24) return isUz ? `${diffHours} soat` : `${diffHours} ч`;
	if (diffDays < 7) return isUz ? `${diffDays} kun` : `${diffDays} д`;

	return date.toLocaleDateString(getLocale(), {
		day: "numeric",
		month: "short",
		timeZone: TIMEZONE,
	});
};

/**
 * Format date for display in UTC+05:00
 */
export const formatDate = (dateString: string): string => {
	const date = parseDate(dateString);
	return date.toLocaleDateString(getLocale(), {
		day: "numeric",
		month: "long",
		year: "numeric",
		timeZone: TIMEZONE,
	});
};

/**
 * Format time for display in UTC+05:00
 */
export const formatTime = (dateString: string): string => {
	const date = parseDate(dateString);
	const time = date.toLocaleTimeString(getLocale(), {
		hour: "2-digit",
		minute: "2-digit",
		timeZone: TIMEZONE,
	});
	return `${time} (${TIMEZONE_LABEL})`;
};

/**
 * Format date and time for display in UTC+05:00
 */
export const formatDateTime = (dateString: string): string => {
	const date = parseDate(dateString);
	const formatted = date.toLocaleString(getLocale(), {
		day: "numeric",
		month: "short",
		hour: "2-digit",
		minute: "2-digit",
		timeZone: TIMEZONE,
	});
	return `${formatted} (${TIMEZONE_LABEL})`;
};

/**
 * Format month and year for display in UTC+05:00
 */
export const formatMonthYear = (dateString: string): string => {
	const date = parseDate(dateString);
	return date.toLocaleDateString(getLocale(), {
		year: "numeric",
		month: "long",
		timeZone: TIMEZONE,
	});
};
