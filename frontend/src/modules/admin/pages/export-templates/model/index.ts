/**
 * Block F V2.0 (F4b) — admin export-templates state.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export interface ExportTemplate {
	id: string;
	platform: string;
	language: string;
	template_body: string;
	is_active: boolean;
	updated_at: string;
}

export interface ExportTemplateCreate {
	platform: string;
	language: string;
	template_body: string;
}

export const fetchExportTemplatesFx = createEffect(async () => {
	const response = await apiClient.get<ExportTemplate[]>(
		"/admin/export-templates",
	);
	return response.data;
});

export const $exportTemplates = restore<ExportTemplate[] | null>(
	fetchExportTemplatesFx.doneData,
	null,
);

export const createExportTemplateFx = createEffect(
	async (payload: ExportTemplateCreate) => {
		const response = await apiClient.post<ExportTemplate>(
			"/admin/export-templates",
			payload,
		);
		return response.data;
	},
);

export const updateExportTemplateFx = createEffect(
	async ({
		id,
		template_body,
		is_active,
	}: {
		id: string;
		template_body?: string;
		is_active?: boolean;
	}) => {
		const response = await apiClient.patch<ExportTemplate>(
			`/admin/export-templates/${id}`,
			{ template_body, is_active },
		);
		return response.data;
	},
);
