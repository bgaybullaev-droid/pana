/**
 * Block F V2.0 (F2) — Stage 2 synonym-hint state.
 *
 * Single effect + dismissed-store. The component owns debounced
 * triggering via useEffect; this module is just the wire.
 */

import { createEffect, createEvent, createStore } from "effector";

import { apiClient } from "@shared/api/client";

export interface SynonymMatch {
	parameter_key: string;
	parameter_value: string | null;
	surface_form: string;
	polarity: "positive" | "negative";
	action: "add" | "contradict" | "ok";
	position: number;
}

export interface AnalyseTextResponse {
	matches: SynonymMatch[];
}

export interface AnalyseTextPayload {
	listingId: string;
	text: string;
	language: string;
	currentParams: Record<string, unknown>;
}

export const analyseTextFx = createEffect(
	async ({ listingId, text, language, currentParams }: AnalyseTextPayload) => {
		const response = await apiClient.post<AnalyseTextResponse>(
			`/listings/${listingId}/analyse-text`,
			{
				text,
				language,
				current_params: currentParams,
			},
		);
		return response.data.matches;
	},
);

/** Per-session dismissed matches — keyed by `${parameter_key}|${action}`. */
export const matchDismissed = createEvent<string>();
export const dismissedReset = createEvent();

export const $dismissedKeys = createStore<Set<string>>(new Set())
	.on(matchDismissed, (state, key) => {
		const next = new Set(state);
		next.add(key);
		return next;
	})
	.reset(dismissedReset);
