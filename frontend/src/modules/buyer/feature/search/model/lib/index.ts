import type { SearchHistoryItem } from "@shared/api/types";

const STORAGE_KEY = "search_history";
export const MAX_HISTORY_ITEMS = 20;

export const loadHistory = (): SearchHistoryItem[] => {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
};

export const saveHistory = (history: SearchHistoryItem[]): void => {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
	} catch {
		// ignore storage errors
	}
};
