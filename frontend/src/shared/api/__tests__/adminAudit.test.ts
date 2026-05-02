/**
 * PR-I — Admin audit log API client tests.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../client";
import { fetchAuditLog, type AuditLogEntry } from "../adminAudit";
import type { PaginatedResponse } from "../types";

const EMPTY_PAGE: PaginatedResponse<AuditLogEntry> = {
	items: [],
	page: 1,
	per_page: 50,
	total: 0,
	total_pages: 0,
};

describe("fetchAuditLog", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /admin/audit-log with params", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: EMPTY_PAGE });
		await fetchAuditLog({
			page: 2,
			per_page: 100,
			entity_type: "listing",
			action: "approve",
		});
		expect(spy).toHaveBeenCalledWith("/admin/audit-log", {
			params: {
				page: 2,
				per_page: 100,
				entity_type: "listing",
				action: "approve",
			},
		});
	});

	it("sends no params when called with empty object", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: EMPTY_PAGE });
		await fetchAuditLog();
		expect(spy).toHaveBeenCalledWith("/admin/audit-log", { params: {} });
	});

	it("returns the full PaginatedResponse verbatim", async () => {
		const payload: PaginatedResponse<AuditLogEntry> = {
			items: [
				{
					id: "11111111-1111-1111-1111-111111111111",
					user_id: null,
					actor_name: null,
					entity_type: "listing",
					entity_id: "22222222-2222-2222-2222-222222222222",
					action: "approve",
					old_values: { moderation_status: "pending" },
					new_values: { moderation_status: "approved" },
					ip_address: "10.0.0.1",
					user_agent: "curl/8",
					created_at: "2026-04-25T12:00:00Z",
				},
			],
			page: 1,
			per_page: 50,
			total: 1,
			total_pages: 1,
		};
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: payload });
		expect(await fetchAuditLog({})).toEqual(payload);
	});

	it("propagates errors (no safe-fallback — page handles it)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("403 Forbidden"));
		await expect(fetchAuditLog({})).rejects.toThrow("403 Forbidden");
	});
});
