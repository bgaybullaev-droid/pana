/**
 * Block F V2.0 (F4b) — admin export-templates console.
 *
 * Lists every template grouped by (platform, language) with body
 * editor + activate toggle. New versions create with ``is_active=false``;
 * the activate button performs the atomic single-statement swap.
 */

import { useEffect, useMemo, useState } from "react";
import {
	Container,
	Stack,
	Title,
	Text,
	Group,
	Button,
	Table,
	Badge,
	Loader,
	Modal,
	Textarea,
	TextInput,
	Code,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useUnit } from "effector-react";

import {
	$exportTemplates,
	createExportTemplateFx,
	fetchExportTemplatesFx,
	updateExportTemplateFx,
	type ExportTemplate,
} from "../../model";

function Page() {
	const rows = useUnit($exportTemplates);
	const loading = useUnit(fetchExportTemplatesFx.pending);
	const [editing, setEditing] = useState<ExportTemplate | null>(null);
	const [createOpen, setCreateOpen] = useState(false);

	useEffect(() => {
		void fetchExportTemplatesFx();
	}, []);

	const grouped = useMemo(() => {
		const map: Record<string, ExportTemplate[]> = {};
		for (const r of rows ?? []) {
			const key = `${r.platform} · ${r.language}`;
			(map[key] ??= []).push(r);
		}
		return map;
	}, [rows]);

	const refresh = () => fetchExportTemplatesFx();

	const onActivate = async (id: string) => {
		await updateExportTemplateFx({ id, is_active: true });
		await refresh();
		notifications.show({ message: "Activated", color: "green" });
	};

	return (
		<Container size={1200} py="md">
			<Stack gap="sm" mb="md">
				<Title order={2}>Export templates</Title>
				<Text size="sm" c="dimmed">
					Block F V2.0 F4 — Cabinet text-export templates per (platform, language).
				</Text>
			</Stack>
			<Group justify="flex-end" mb="md">
				<Button onClick={() => setCreateOpen(true)}>New template</Button>
			</Group>
			{loading || !rows ? (
				<Loader />
			) : (
				<Stack gap="md">
					{Object.entries(grouped).map(([key, group]) => (
						<Stack key={key} gap={4}>
							<Title order={5}>{key}</Title>
							<Table withTableBorder striped>
								<Table.Thead>
									<Table.Tr>
										<Table.Th style={{ width: 80 }}>Active</Table.Th>
										<Table.Th>Body (preview)</Table.Th>
										<Table.Th style={{ width: 180 }}>Updated</Table.Th>
										<Table.Th style={{ width: 200 }} />
									</Table.Tr>
								</Table.Thead>
								<Table.Tbody>
									{group.map((r) => (
										<Table.Tr key={r.id}>
											<Table.Td>
												{r.is_active ? (
													<Badge color="green">active</Badge>
												) : (
													<Badge color="gray" variant="light">
														inactive
													</Badge>
												)}
											</Table.Td>
											<Table.Td>
												<Text
													size="xs"
													style={{
														whiteSpace: "pre-wrap",
														maxHeight: 80,
														overflow: "hidden",
													}}
												>
													{r.template_body.slice(0, 200)}
												</Text>
											</Table.Td>
											<Table.Td>
												<Text size="xs" c="dimmed">
													{new Date(r.updated_at).toLocaleString()}
												</Text>
											</Table.Td>
											<Table.Td>
												<Group gap="xs" justify="flex-end">
													<Button
														size="xs"
														variant="subtle"
														onClick={() => setEditing(r)}
													>
														Edit
													</Button>
													{!r.is_active && (
														<Button size="xs" onClick={() => onActivate(r.id)}>
															Activate
														</Button>
													)}
												</Group>
											</Table.Td>
										</Table.Tr>
									))}
								</Table.Tbody>
							</Table>
						</Stack>
					))}
				</Stack>
			)}
			<EditTemplateModal
				row={editing}
				onClose={() => setEditing(null)}
				onSaved={refresh}
			/>
			<CreateTemplateModal
				opened={createOpen}
				onClose={() => setCreateOpen(false)}
				onCreated={refresh}
			/>
		</Container>
	);
}

interface EditProps {
	row: ExportTemplate | null;
	onClose: () => void;
	onSaved: () => void;
}

function EditTemplateModal({ row, onClose, onSaved }: EditProps) {
	const [body, setBody] = useState("");
	const [busy, setBusy] = useState(false);

	useEffect(() => {
		setBody(row?.template_body ?? "");
	}, [row]);

	const save = async () => {
		if (!row) return;
		setBusy(true);
		try {
			await updateExportTemplateFx({ id: row.id, template_body: body });
			notifications.show({ message: "Saved", color: "green" });
			onSaved();
			onClose();
		} finally {
			setBusy(false);
		}
	};

	if (!row) return null;
	return (
		<Modal
			opened
			onClose={onClose}
			title={`Edit ${row.platform} · ${row.language}`}
			size="xl"
		>
			<Stack gap="sm">
				<Text size="xs" c="dimmed">
					Allowed placeholders:&nbsp;
					<Code>title</Code>, <Code>description</Code>, <Code>price_formatted</Code>,{" "}
					<Code>district</Code>, <Code>rooms</Code>, <Code>area</Code>,{" "}
					<Code>signature</Code>, <Code>cta</Code>, <Code>extra_hashtags</Code>,{" "}
					<Code>listing_url</Code>. Control blocks <Code>{`{% %}`}</Code> are
					rejected.
				</Text>
				<Textarea
					value={body}
					onChange={(e) => setBody(e.currentTarget.value)}
					minRows={15}
					autosize
				/>
				<Group justify="flex-end">
					<Button variant="subtle" onClick={onClose}>
						Cancel
					</Button>
					<Button onClick={save} loading={busy} disabled={!body.trim()}>
						Save
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

interface CreateProps {
	opened: boolean;
	onClose: () => void;
	onCreated: () => void;
}

function CreateTemplateModal({ opened, onClose, onCreated }: CreateProps) {
	const [platform, setPlatform] = useState("");
	const [language, setLanguage] = useState("");
	const [body, setBody] = useState("");
	const [busy, setBusy] = useState(false);

	const save = async () => {
		setBusy(true);
		try {
			await createExportTemplateFx({
				platform: platform.trim(),
				language: language.trim(),
				template_body: body,
			});
			notifications.show({ message: "Created (inactive)", color: "green" });
			setPlatform("");
			setLanguage("");
			setBody("");
			onCreated();
			onClose();
		} finally {
			setBusy(false);
		}
	};

	return (
		<Modal opened={opened} onClose={onClose} title="New template" size="xl">
			<Stack gap="sm">
				<Group grow>
					<TextInput
						label="Platform"
						placeholder="olx / telegram_channel / instagram"
						value={platform}
						onChange={(e) => setPlatform(e.currentTarget.value)}
					/>
					<TextInput
						label="Language"
						placeholder="ru / uz / uz_cyrl"
						value={language}
						onChange={(e) => setLanguage(e.currentTarget.value)}
					/>
				</Group>
				<Textarea
					label="Body"
					value={body}
					onChange={(e) => setBody(e.currentTarget.value)}
					minRows={10}
					autosize
				/>
				<Group justify="flex-end">
					<Button variant="subtle" onClick={onClose}>
						Cancel
					</Button>
					<Button
						onClick={save}
						loading={busy}
						disabled={!platform.trim() || !language.trim() || !body.trim()}
					>
						Create
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

export const AdminExportTemplates = {
	route: "/admin/export-templates",
	Page,
};
