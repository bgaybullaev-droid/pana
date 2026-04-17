/**
 * PR-I — Admin audit log API client.
 *
 * Backs the `/admin/audit` page. Paginated, filterable view over the
 * server's audit_log table. See `backend/app/api/v1/admin.py` route
 * `GET /admin/audit-log`.
 */

import { apiClient } from "./client";
import type { PaginatedResponse } from "./types";

export interface AuditLogEntry {
	id: string;
	user_id: string | null;
	actor_name: string | null;
	entity_type: string;
	entity_id: string;
	action: string;
	old_values: Record<string, unknown> | null;
	new_values: Record<string, unknown> | null;
	ip_address: string | null;
	user_agent: string | null;
	created_at: string;
}

export interface AuditLogQueryParams {
	page?: number;
	per_page?: number;
	entity_type?: string;
	action?: string;
	user_id?: string;
	from_date?: string; // ISO-8601
	to_date?: string; // ISO-8601
}

export async function fetchAuditLog(
	params: AuditLogQueryParams = {},
): Promise<PaginatedResponse<AuditLogEntry>> {
	const response = await apiClient.get<PaginatedResponse<AuditLogEntry>>(
		"/admin/audit-log",
		{ params },
	);
	return response.data;
}
