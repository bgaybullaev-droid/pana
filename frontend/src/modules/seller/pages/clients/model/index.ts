/**
 * Phase-2 seller CRM — Effector state.
 *
 * CRUD effects + pipeline-stage helpers for /seller/clients. The
 * Kanban view groups ``$clients`` by ``pipeline_stage``; the
 * change-stage button calls ``updateClientFx`` with just the new
 * stage so the back-end remains the source of truth.
 */

import { createEffect, createStore } from "effector";

import { apiClient } from "@shared/api/client";

export const PIPELINE_STAGES = [
	"new",
	"contacted",
	"viewing",
	"negotiating",
	"won",
	"lost",
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export interface SellerClient {
	id: string;
	seller_id: string;
	name: string;
	phone: string | null;
	notes: string | null;
	pipeline_stage: PipelineStage;
	created_at: string;
	updated_at: string;
}

export interface AttachedListing {
	listing_id: string;
	added_at: string;
}

export interface SellerClientDetail extends SellerClient {
	listings: AttachedListing[];
}

export interface SellerClientCreate {
	name: string;
	phone?: string;
	notes?: string;
	pipeline_stage?: PipelineStage;
}

export interface SellerClientUpdate {
	name?: string;
	phone?: string;
	notes?: string;
	pipeline_stage?: PipelineStage;
}

export const fetchClientsFx = createEffect(
	async (filter: { pipeline_stage?: PipelineStage } = {}) => {
		const response = await apiClient.get<SellerClient[]>("/seller/clients", {
			params: filter,
		});
		return response.data;
	},
);

export const fetchClientDetailFx = createEffect(async (id: string) => {
	const response = await apiClient.get<SellerClientDetail>(
		`/seller/clients/${id}`,
	);
	return response.data;
});

export const createClientFx = createEffect(
	async (payload: SellerClientCreate) => {
		const response = await apiClient.post<SellerClient>(
			"/seller/clients",
			payload,
		);
		return response.data;
	},
);

export const updateClientFx = createEffect(
	async ({ id, ...payload }: { id: string } & SellerClientUpdate) => {
		const response = await apiClient.patch<SellerClient>(
			`/seller/clients/${id}`,
			payload,
		);
		return response.data;
	},
);

export const deleteClientFx = createEffect(async (id: string) => {
	await apiClient.delete(`/seller/clients/${id}`);
	return id;
});

export const attachListingFx = createEffect(
	async ({ clientId, listingId }: { clientId: string; listingId: string }) => {
		const response = await apiClient.post<AttachedListing>(
			`/seller/clients/${clientId}/attach/${listingId}`,
		);
		return { clientId, attached: response.data };
	},
);

export const detachListingFx = createEffect(
	async ({ clientId, listingId }: { clientId: string; listingId: string }) => {
		await apiClient.delete(`/seller/clients/${clientId}/attach/${listingId}`);
		return { clientId, listingId };
	},
);

export const $clients = createStore<SellerClient[]>([])
	.on(fetchClientsFx.doneData, (_, rows) => rows)
	.on(createClientFx.doneData, (state, row) => [row, ...state])
	.on(updateClientFx.doneData, (state, row) =>
		state.map((c) => (c.id === row.id ? row : c)),
	)
	.on(deleteClientFx.done, (state, { params }) =>
		state.filter((c) => c.id !== params),
	);
