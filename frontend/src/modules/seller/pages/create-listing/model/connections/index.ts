/**
 * Block F V2.0 (F1) — create-listing event wiring.
 *
 * The polling loop is driven from the component (useEffect with
 * setInterval) so it can be cleaned up on unmount/Stage-1 transition.
 * This file glues the events / effects / stores so the component
 * stays a thin shell.
 */

import "../stores";
import "../effects";
import "../events";

import { sample } from "effector";

import {
	createDraftListingFx,
	fetchDraftPreviewFx,
} from "@shared/state/listing/model";

// After the draft is created, kick off the first preview fetch
// immediately so Stage 2 mounts with a known state baseline.
sample({
	clock: createDraftListingFx.doneData,
	fn: (data) => data.id,
	target: fetchDraftPreviewFx,
});
