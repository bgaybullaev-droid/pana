/**
 * Block F V2.0 (F1) — create-listing two-step flow state.
 *
 * Stage 1 = parameters + photos. Stage 2 = AI preview + edit + publish.
 *
 * The Effector graph below + `connections/index.ts` (wiring) drive
 * every transition. The Page component only reads stores via
 * `useUnit` and dispatches events; no setState in the component.
 */

import { createStore } from "effector";

import {
	createDraftListingFx,
	fetchDraftPreviewFx,
	publishDraftFx,
	regenerateDraftFx,
	type DraftPreviewData,
	type ListingCreateData,
} from "@shared/state/listing/model";

import {
	editDescription,
	hydrateDraftPreview,
	pollingTimedOut,
	resetDraftFlow,
	stageAdvance,
	stageBackToParams,
	startAiGeneration,
} from "../events";

export type Stage = 1 | 2;

export type EditedDescriptions = {
	ru: string;
	uz: string;
	uz_cyrl: string;
};

const EMPTY_EDITS: EditedDescriptions = { ru: "", uz: "", uz_cyrl: "" };

/** Current Stage (1 = params + AI, 2 = preview/publish). */
export const $stage = createStore<Stage>(1)
	.on(stageAdvance, () => 2)
	.on(stageBackToParams, () => 1)
	.reset(resetDraftFlow);

/** The Listing UUID created at Stage 1 → Stage 2 transition. */
export const $draftId = createStore<string | null>(null)
	.on(createDraftListingFx.doneData, (_, data) => data.id)
	.reset(resetDraftFlow);

/** The full form payload submitted in Stage 1 — used to build the preview listing. */
export const $draftFormData = createStore<ListingCreateData | null>(null)
	.on(createDraftListingFx.done, (_, { params }) => params)
	.reset(resetDraftFlow);

/** Full preview payload (poll target). */
export const $draftPreview = createStore<DraftPreviewData | null>(null)
	.on(fetchDraftPreviewFx.doneData, (_, data) => data)
	.on(hydrateDraftPreview, (_, data) => data)
	.reset(resetDraftFlow);

/** Per-language editable descriptions. Seeded from `$draftPreview` once
 *  AI text arrives. Preserved on Stage-2 → Stage-1 → Stage-2 transit
 *  unless the user clicks "Обновить" on the param-change banner. */
export const $editedDescriptions = createStore<EditedDescriptions>(EMPTY_EDITS)
	.on(fetchDraftPreviewFx.doneData, (prev, data) => {
		// Only seed if the seller hasn't typed anything yet (any field
		// non-empty means they've edited). Subsequent polls during edit
		// must not clobber edits.
		const hasEdits =
			prev.ru.length > 0 || prev.uz.length > 0 || prev.uz_cyrl.length > 0;
		if (hasEdits) return prev;
		if (!data.ai_description_ru) return prev;
		return {
			ru: data.ai_description_ru ?? "",
			uz: data.ai_description_uz ?? "",
			uz_cyrl: data.ai_description_uz_cyrl ?? "",
		};
	})
	.on(editDescription, (state, { lang, value }) => ({
		...state,
		[lang]: value,
	}))
	.on(regenerateDraftFx.done, () => EMPTY_EDITS)
	.reset(resetDraftFlow);

/** True while Stage 2 is awaiting the first AI text. */
export const $isPolling = createStore<boolean>(false)
	.on(startAiGeneration, () => true) // user opted-in
	.on(fetchDraftPreviewFx.doneData, (state, data) =>
		// stop polling as soon as ru text appears
		data.ai_description_ru ? false : state,
	)
	.on(pollingTimedOut, () => false)
	.on(regenerateDraftFx.done, () => true) // re-poll after regen
	.reset(resetDraftFlow);

/** Polling exceeded 30s — surface manual "Обновить" button. */
export const $pollingTimedOut = createStore<boolean>(false)
	.on(pollingTimedOut, () => true)
	.on(fetchDraftPreviewFx.doneData, (state, data) =>
		data.ai_description_ru ? false : state,
	)
	.on(regenerateDraftFx.done, () => false)
	.reset(resetDraftFlow);

/** Loading flags piped from shared effects for the UI. */
export const $isCreatingDraft = createDraftListingFx.pending;
export const $isRegenerating = regenerateDraftFx.pending;
export const $isPublishing = publishDraftFx.pending;
