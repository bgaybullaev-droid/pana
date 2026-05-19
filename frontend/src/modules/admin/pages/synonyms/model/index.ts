/**
 * Block F V2.0 (F2) — admin synonyms console state.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export interface SynonymEntry {
	id: string;
	parameter_key: string;
	parameter_value: string | null;
	surface_form: string;
	language: string;
	polarity: "positive" | "negative";
	created_at: string;
}

export interface SynonymCreate {
	parameter_key: string;
	parameter_value?: string;
	surface_form: string;
	language: string;
	polarity?: "positive" | "negative";
}

export const fetchSynonymsFx = createEffect(
	async (query: { parameter_key?: string; language?: string } = {}) => {
		const response = await apiClient.get<SynonymEntry[]>("/admin/synonyms", {
			params: query,
		});
		return response.data;
	},
);

export const $synonyms = restore<SynonymEntry[] | null>(
	fetchSynonymsFx.doneData,
	null,
);

export const bulkCreateSynonymsFx = createEffect(
	async (entries: SynonymCreate[]) => {
		const response = await apiClient.post<{
			inserted: number;
			skipped: number;
			items: SynonymEntry[];
		}>("/admin/synonyms", { entries });
		return response.data;
	},
);

export const deleteSynonymFx = createEffect(async (id: string) => {
	await apiClient.delete(`/admin/synonyms/${id}`);
	return id;
});
