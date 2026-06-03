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

/** User clicked "Back" from Stage 2; preserve in-flight edits + draftId. */
export const stageBackToParams = createEvent();

/** User edits a per-language textarea on Stage 2. */
export const editDescription = createEvent<{
	lang: "ru" | "uz" | "uz_cyrl";
	value: string;
}>();

/** User dismissed the param-change banner on Stage 2 ("Оставить как есть"). */
export const dismissParamChangeBanner = createEvent();

/** Polling exceeded the 30s budget without success. */
export const pollingTimedOut = createEvent();

/** Stage 2 — full reset on publish success or explicit cancel. */
export const resetDraftFlow = createEvent();

/** Manual draft-preview rehydrate (used by Stage 2 mount + manual retry). */
export const hydrateDraftPreview = createEvent<DraftPreviewData>();

/** Stage 2 — current key params (for param-change drift detection). */
export const setCurrentParamSnapshot = createEvent<
	Record<string, unknown> | null
>();

/** User clicked "Сгенерировать с AI" — starts the polling loop. */
export const startAiGeneration = createEvent();
