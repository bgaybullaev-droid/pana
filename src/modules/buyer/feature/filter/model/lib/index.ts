import type { Region, SortingOption } from "@shared/api/types";

export const sortingOptions: SortingOption[] = [
	{ id: 0, label: "Newest" },
	{ id: 1, label: "Price: Low to High" },
	{ id: 2, label: "Price: High to Low" },
];

export const defaultRegions: Region[] = [
	{ id: "tashkent", name: "Tashkent" },
	{ id: "tashkent_region", name: "Tashkent Region" },
	{ id: "samarkand", name: "Samarkand" },
	{ id: "bukhara", name: "Bukhara" },
	{ id: "fergana", name: "Fergana" },
	{ id: "andijan", name: "Andijan" },
	{ id: "namangan", name: "Namangan" },
	{ id: "kashkadarya", name: "Kashkadarya" },
	{ id: "surkhandarya", name: "Surkhandarya" },
	{ id: "jizzakh", name: "Jizzakh" },
	{ id: "syrdarya", name: "Syrdarya" },
	{ id: "khorezm", name: "Khorezm" },
	{ id: "navoi", name: "Navoi" },
	{ id: "karakalpakstan", name: "Karakalpakstan" },
];
