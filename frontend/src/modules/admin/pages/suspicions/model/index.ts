/**
 * Phase-2 admin duplicate-account suspicions queue — Effector state.
 *
 * Reads + decision effects against ``/admin/suspicions``. The detail
 * drawer reuses the row data from the list (no extra ``GET /:id`` is
 * needed for the standard flow); ``decideSuspicionFx`` mirrors the
 * back-end's three legal decisions.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export type SuspicionStatus = "open" | "reviewed" | "dismissed" | "merged";
export type SuspicionDecision = "merged" | "dismissed" | "reviewed";

export interface Suspicion {
	id: string;
	primary_user_id: string;
	signal_kind: string;
	evidence: Record<string, unknown>;
	status: SuspicionStatus;
	reviewed_by: string | null;
	reviewed_at: string | null;
	notes: string | null;
	created_at: string;
}

export interface SuspicionListQuery {
	status?: SuspicionStatus;
	signal_kind?: string;
	page?: number;
}

export const fetchSuspicionsFx = createEffect(
	async (query: SuspicionListQuery = {}) => {
		const response = await apiClient.get<Suspicion[]>("/admin/suspicions", {
			params: {
				status: query.status ?? "open",
				signal_kind: query.signal_kind || undefined,
				page: query.page ?? 1,
			},
		});
		return response.data;
	},
);

export const $suspicions = restore<Suspicion[] | null>(
	fetchSuspicionsFx.doneData,
	null,
);

export const decideSuspicionFx = createEffect(
	async (payload: {
		id: string;
		decision: SuspicionDecision;
		notes?: string;
	}) => {
		const response = await apiClient.post<Suspicion>(
			`/admin/suspicions/${payload.id}/decide`,
			{ decision: payload.decision, notes: payload.notes },
		);
		return response.data;
	},
);
