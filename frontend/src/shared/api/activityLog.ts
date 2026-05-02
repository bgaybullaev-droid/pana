import { apiClient } from "./client";
import type { ActivityLogPayload } from "./types";

/**
 * Fire-and-forget activity logger.
 * Never throws — errors are silently swallowed so they don't affect UX.
 * Called by: likes, listing views, search queries, saved searches.
 */
export const activityLogApi = {
	log: (payload: ActivityLogPayload): void => {
		apiClient
			.post("/activity-log", payload)
			.catch(() => {
				// intentionally silent - logging must not break the main flow
			});
	},
};
