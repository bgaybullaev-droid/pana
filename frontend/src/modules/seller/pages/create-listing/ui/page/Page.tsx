/**
 * Block F V2.0 (F1) — create-listing top-level page.
 *
 * Thin wrapper that switches between Stage 1 (params + photos) and
 * Stage 2 (AI preview + edit + publish) based on Effector state.
 *
 * Stage transitions:
 *   Stage 1 → Stage 2  : on POST /listings/draft success (store reducer)
 *   Stage 2 → Stage 1  : on user "Назад" click (stageBackToParams event)
 *   any → reset        : on full page unmount (cleanup) and on publish
 *                        success (publishDraftFx → resetDraftFlow inside
 *                        Stage 2 handler)
 */

import { useEffect } from "react";
import { useUnit } from "effector-react";

// Trigger connections (sample wiring) at module load.
import "../../model/connections";

import { $stage } from "../../model/stores";
import { resetDraftFlow } from "../../model/events";

import Stage1 from "./Stage1";
import Stage2 from "./Stage2";

function Page() {
	const stage = useUnit($stage);

	// Full-flow reset on page unmount so revisiting /seller/create starts
	// from Stage 1 with no leftover draftId / edits / polling state.
	useEffect(() => {
		return () => {
			resetDraftFlow();
		};
	}, []);

	if (stage === 2) {
		return <Stage2 />;
	}
	return <Stage1 />;
}

export const CreateListing = {
	route: "/seller/create",
	Page,
};
