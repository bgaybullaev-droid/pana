/**
 * Block F V2.0 (F5b) — admin AI-quality state.
 *
 * Thin effector model exposing the 4-tab payloads:
 *   - metrics overview
 *   - generations list (with detail-on-demand)
 *   - feedback queue
 *   - prompt versions
 *
 * No store coupling between tabs — each tab fetches independently via
 * its effect, which means navigating tabs never blocks the UI on a
 * sibling-tab refresh.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

// ───────────────────────────────────────────────────────────
// Metrics
// ───────────────────────────────────────────────────────────

export interface MetricsSnapshot {
	window_hours: number;
	total_generations: number;
	ok_count: number;
	fallback_count: number;
	failure_count: number;
	bad_feedback_count: number;
	bad_feedback_rate: number;
	duration_p50_ms: number | null;
	duration_p95_ms: number | null;
	cost_usd_today: number;
	alert_states: Record<string, boolean>;
}

export const fetchMetricsFx = createEffect(async () => {
	const response = await apiClient.get<MetricsSnapshot>("/admin/ai/metrics");
	return response.data;
});

export const $metrics = restore<MetricsSnapshot | null>(
	fetchMetricsFx.doneData,
	null,
);

// ───────────────────────────────────────────────────────────
// Generations
// ───────────────────────────────────────────────────────────

export interface GenerationSummary {
	id: string;
	listing_id: string | null;
	prompt_template_id: string | null;
	model: string;
	duration_ms: number;
	input_tokens: number | null;
	output_tokens: number | null;
	cost_usd_micros: number | null;
	triggered_by: string;
	outcome: string;
	created_at: string;
}

export interface GenerationDetail extends GenerationSummary {
	prompt_text: string;
	response_text: string;
}

export interface GenerationsList {
	total: number;
	page: number;
	items: GenerationSummary[];
}

export interface GenerationsQuery {
	page?: number;
	page_size?: number;
	date_from?: string;
	date_to?: string;
	lang?: string;
	model?: string;
	outcome?: string;
	has_feedback?: boolean;
}

export const fetchGenerationsFx = createEffect(
	async (query: GenerationsQuery = {}) => {
		const response = await apiClient.get<GenerationsList>(
			"/admin/ai/generations",
			{ params: query },
		);
		return response.data;
	},
);

export const $generations = restore<GenerationsList | null>(
	fetchGenerationsFx.doneData,
	null,
);

export const fetchGenerationDetailFx = createEffect(async (id: string) => {
	const response = await apiClient.get<GenerationDetail>(
		`/admin/ai/generations/${id}`,
	);
	return response.data;
});

export const $generationDetail = restore<GenerationDetail | null>(
	fetchGenerationDetailFx.doneData,
	null,
);

// ───────────────────────────────────────────────────────────
// Feedback queue
// ───────────────────────────────────────────────────────────

export interface FeedbackRow {
	id: string;
	generation_id: string | null;
	listing_id: string | null;
	user_id: string;
	category: string;
	comment: string | null;
	handled: boolean;
	created_at: string;
}

export interface FeedbackList {
	total: number;
	page: number;
	items: FeedbackRow[];
}

export const fetchFeedbackQueueFx = createEffect(
	async ({
		handled = false,
		page = 1,
	}: { handled?: boolean; page?: number } = {}) => {
		const response = await apiClient.get<FeedbackList>("/admin/ai/feedback", {
			params: { handled, page },
		});
		return response.data;
	},
);

export const $feedbackQueue = restore<FeedbackList | null>(
	fetchFeedbackQueueFx.doneData,
	null,
);

export const handleFeedbackFx = createEffect(async (id: string) => {
	const response = await apiClient.post<FeedbackRow>(
		`/admin/ai/feedback/${id}/handle`,
	);
	return response.data;
});

// ───────────────────────────────────────────────────────────
// Prompt versions
// ───────────────────────────────────────────────────────────

export interface PromptTemplate {
	id: string;
	kind: string;
	version: number;
	body: string;
	model_hint: string | null;
	is_active: boolean;
	notes: string | null;
	created_by_user_id: string | null;
	created_at: string;
}

export const fetchPromptsFx = createEffect(async (kind?: string) => {
	const response = await apiClient.get<PromptTemplate[]>("/admin/ai/prompts", {
		params: kind ? { kind } : {},
	});
	return response.data;
});

export const $prompts = restore<PromptTemplate[] | null>(
	fetchPromptsFx.doneData,
	null,
);

export interface CreatePromptPayload {
	kind: string;
	body: string;
	model_hint?: string;
	notes?: string;
}

export const createPromptFx = createEffect(async (payload: CreatePromptPayload) => {
	const response = await apiClient.post<PromptTemplate>(
		"/admin/ai/prompts",
		payload,
	);
	return response.data;
});

export const activatePromptFx = createEffect(async (id: string) => {
	const response = await apiClient.post<PromptTemplate>(
		`/admin/ai/prompts/${id}/activate`,
	);
	return response.data;
});
