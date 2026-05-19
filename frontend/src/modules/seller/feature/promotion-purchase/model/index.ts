/**
 * Block phase-2 — seller promotion-purchase effects.
 *
 * Thin wrapper around the three /seller/listings/{id}/promotions/*
 * endpoints. Each effect surfaces a 402 ("insufficient_funds") as a
 * typed error the UI can branch on (-> "Top up wallet" CTA).
 */

import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

export type PromotionKind = "urgent" | "notify_priority" | "boost";

export interface PromotionResponse {
	listing_id: string;
	kind: PromotionKind;
	active_until: string;
	amount_charged: number;
	balance_after: number;
}

export interface BuyPromotionInput {
	listing_id: string;
	duration_days?: number;
}

// Hardcoded prices, mirror backend constants for v1.
export const PROMOTION_PRICES_UZS: Record<PromotionKind, number> = {
	urgent: 5_000,
	notify_priority: 20_000,
	boost: 2_000, // per day
};

export const PROMOTION_DEFAULT_DAYS: Record<PromotionKind, number> = {
	urgent: 7,
	notify_priority: 30,
	boost: 1,
};

function pathFor(kind: PromotionKind): string {
	if (kind === "notify_priority") return "notify-priority";
	return kind;
}

export class InsufficientFundsError extends Error {
	constructor() {
		super("insufficient_funds");
		this.name = "InsufficientFundsError";
	}
}

export const buyPromotionFx = createEffect(
	async ({
		listing_id,
		kind,
		duration_days,
	}: BuyPromotionInput & { kind: PromotionKind }): Promise<PromotionResponse> => {
		try {
			const response = await apiClient.post<PromotionResponse>(
				`/seller/listings/${listing_id}/promotions/${pathFor(kind)}`,
				{ duration_days: duration_days ?? PROMOTION_DEFAULT_DAYS[kind] },
			);
			return response.data;
		} catch (err: unknown) {
			const status = (err as { response?: { status?: number } })?.response
				?.status;
			if (status === 402) {
				throw new InsufficientFundsError();
			}
			throw err;
		}
	},
);
