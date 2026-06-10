import { useMemo } from "react";
import type { ListingFormValues, ListingFormMode } from "./useListingForm";
import {
	getFirstIncompleteSection,
	getRequiredProgress,
	getSectionStates,
	type SectionKey,
	type SectionState,
} from "../lib/requiredness";

export interface ListingCompleteness {
	sectionStates: Record<SectionKey, SectionState>;
	progress: { filled: number; total: number };
	/** All required fields (incl. photos) are filled. */
	isComplete: boolean;
	firstIncompleteSection: SectionKey | null;
}

/**
 * Derives live section statuses + overall required-field progress for the
 * listing create/edit pages from the shared requiredness table.
 */
export function useListingCompleteness(args: {
	values: ListingFormValues;
	mode: ListingFormMode;
	imageCount: number;
	submitAttempted: boolean;
}): ListingCompleteness {
	const { values, mode, imageCount, submitAttempted } = args;
	return useMemo(() => {
		const progress = getRequiredProgress(values, mode, imageCount);
		return {
			sectionStates: getSectionStates(values, mode, imageCount, submitAttempted),
			progress,
			isComplete: progress.filled === progress.total,
			firstIncompleteSection: getFirstIncompleteSection(
				values,
				mode,
				imageCount,
			),
		};
	}, [values, mode, imageCount, submitAttempted]);
}
