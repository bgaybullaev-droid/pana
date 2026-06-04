/**
 * Block F V2.0 (F1) — create-listing local events.
 *
 * Events shape the Stage 1 → Stage 2 → publish flow. The store
 * connections below subscribe to these + the shared effects in
 * @shared/state/listing/model to advance the state machine.
 */

import { createEvent } from "effector";

import type { DraftPreviewData } from "@shared/state/listing/model";

export const pageMounted = createEvent();

/** User clicked "Редактировать" from Stage 2; preserve in-flight edits + draftId. */
export const stageBackToParams = createEvent();

/** User edits a per-language textarea on Stage 1. */
export const editDescription = createEvent<{
	lang: "ru" | "uz" | "uz_cyrl";
	value: string;
}>();

/** Polling exceeded the 30s budget without success. */
export const pollingTimedOut = createEvent();

/** Stage 2 — full reset on publish success or explicit cancel. */
export const resetDraftFlow = createEvent();

/** Manual draft-preview rehydrate (used by manual retry). */
export const hydrateDraftPreview = createEvent<DraftPreviewData>();

/** User clicked "Сгенерировать с AI" in Stage 1 — starts the polling loop. */
export const startAiGeneration = createEvent();

/** User ready to advance to Stage 2 (draft already exists or just created). */
export const stageAdvance = createEvent();
