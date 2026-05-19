/**
 * Block F V2.0 (F5b) — AI feedback effector model.
 *
 * Single effect that POSTs one row to ``/ai-feedback``. The component
 * layer owns local open/close state for the modal; this file only
 * exposes the effect + types so all callers share one wire shape.
 */

import { createEffect } from "effector";

import { apiClient } from "@shared/api/client";

export type FeedbackCategory =
	| "grammar"
	| "unnatural"
	| "factual"
	| "too_long"
	| "too_short"
	| "other";

export interface SubmitFeedbackPayload {
	generation_id?: string;
	listing_id: string;
	category: FeedbackCategory;
	comment?: string;
}

export interface FeedbackResponse {
	id: string;
	generation_id: string | null;
	listing_id: string | null;
	user_id: string;
	category: string;
	comment: string | null;
	handled: boolean;
	created_at: string;
}

export const submitFeedbackFx = createEffect(
	async (payload: SubmitFeedbackPayload) => {
		const response = await apiClient.post<FeedbackResponse>(
			"/ai-feedback",
			payload,
		);
		return response.data;
	},
);
