/**
 * Block F V2.0 (F2) — admin synonym dictionary console.
 *
 * List view with two filters (parameter_key, language), an inline
 * delete-row action, and a CSV-paste bulk-import modal. CSV format:
 * one entry per line, comma-separated:
 *
 *   ``parameter_key,parameter_value,surface_form,language,polarity``
 *
 * Empty parameter_value column allowed (boolean-style params).
 */

import { useEffect, useState } from "react";
import {
	Container,
	Stack,
	Title,
	Text,
	Group,
	TextInput,
	Button,
	Table,
	Badge,
	Loader,
	Modal,
	Textarea,
	Code,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconTrash, IconUpload } from "@tabler/icons-react";
import { useUnit } from "effector-react";

import {
	$synonyms,
	bulkCreateSynonymsFx,
	deleteSynonymFx,
	fetchSynonymsFx,
	type SynonymCreate,
} from "../../model";

function Page() {
	const rows = useUnit($synonyms);
	const loading = useUnit(fetchSynonymsFx.pending);
	const [parameterKey, setParameterKey] = useState("");
	const [language, setLanguage] = useState("");
	const [bulkOpen, setBulkOpen] = useState(false);

	useEffect(() => {
		void fetchSynonymsFx({
			parameter_key: parameterKey || undefined,
			language: language || undefined,
		});
	}, [parameterKey, language]);

	const refresh = () =>
		fetchSynonymsFx({
			parameter_key: parameterKey || undefined,
			language: language || undefined,
		});

	const onDelete = async (id: string) => {
		await deleteSynonymFx(id);
		await refresh();
	};

	return (
		<Container size={1200} py="md">
			<Stack gap="sm" mb="md">
				<Title order={2}>Synonyms</Title>
				<Text size="sm" c="dimmed">
					Block F V2.0 F2 — surface form → structured parameter mapping for
					Stage-2 text hints.
				</Text>
			</Stack>
			<Group gap="sm" mb="md">
				<TextInput
					placeholder="parameter_key"
					value={parameterKey}
					onChange={(e) => setParameterKey(e.currentTarget.value)}
				/>
				<TextInput
					placeholder="language (ru / uz / uz_cyrl / *)"
					value={language}
					onChange={(e) => setLanguage(e.currentTarget.value)}
				/>
				<Button leftSection={<IconUpload size={14} />} onClick={() => setBulkOpen(true)}>
					Bulk import
				</Button>
			</Group>
			{loading || !rows ? (
				<Loader />
			) : (
				<Table withTableBorder striped highlightOnHover>
					<Table.Thead>
						<Table.Tr>
							<Table.Th>Parameter</Table.Th>
							<Table.Th>Value</Table.Th>
							<Table.Th>Surface form</Table.Th>
							<Table.Th>Lang</Table.Th>
							<Table.Th>Polarity</Table.Th>
							<Table.Th />
						</Table.Tr>
					</Table.Thead>
					<Table.Tbody>
						{rows.map((r) => (
							<Table.Tr key={r.id}>
								<Table.Td><Code>{r.parameter_key}</Code></Table.Td>
								<Table.Td>{r.parameter_value ?? <Text c="dimmed">—</Text>}</Table.Td>
								<Table.Td>{r.surface_form}</Table.Td>
								<Table.Td>
									<Badge variant="light" size="sm">{r.language}</Badge>
								</Table.Td>
								<Table.Td>
									<Badge color={r.polarity === "positive" ? "green" : "orange"} size="sm">
										{r.polarity}
									</Badge>
								</Table.Td>
								<Table.Td>
									<Button
										size="xs"
										color="red"
										variant="subtle"
										leftSection={<IconTrash size={12} />}
										onClick={() => onDelete(r.id)}
									>
										Delete
									</Button>
								</Table.Td>
							</Table.Tr>
						))}
						{rows.length === 0 && (
							<Table.Tr>
								<Table.Td colSpan={6}>
									<Text size="sm" c="dimmed" ta="center">
										No synonyms match the current filters.
									</Text>
								</Table.Td>
							</Table.Tr>
						)}
					</Table.Tbody>
				</Table>
			)}
			<BulkImportModal
				opened={bulkOpen}
				onClose={() => setBulkOpen(false)}
				onDone={refresh}
			/>
		</Container>
	);
}

interface BulkProps {
	opened: boolean;
	onClose: () => void;
	onDone: () => void;
}

function BulkImportModal({ opened, onClose, onDone }: BulkProps) {
	const [csv, setCsv] = useState("");
	const [busy, setBusy] = useState(false);

	const parse = (raw: string): SynonymCreate[] => {
		const out: SynonymCreate[] = [];
		for (const line of raw.split(/\r?\n/)) {
			const trimmed = line.trim();
			if (!trimmed || trimmed.startsWith("#")) continue;
			const parts = trimmed.split(",").map((p) => p.trim());
			if (parts.length < 4) continue;
			const [parameter_key, parameter_value, surface_form, lang, polarity] = parts;
			if (!parameter_key || !surface_form || !lang) continue;
			out.push({
				parameter_key,
				parameter_value: parameter_value || undefined,
				surface_form,
				language: lang,
				polarity: (polarity as "positive" | "negative") || "positive",
			});
		}
		return out;
	};

	const submit = async () => {
		const entries = parse(csv);
		if (entries.length === 0) {
			notifications.show({ message: "No valid rows parsed", color: "red" });
			return;
		}
		setBusy(true);
		try {
			const result = await bulkCreateSynonymsFx(entries);
			notifications.show({
				message: `Inserted ${result.inserted} (skipped ${result.skipped})`,
				color: "green",
			});
			setCsv("");
			onDone();
			onClose();
		} finally {
			setBusy(false);
		}
	};

	return (
		<Modal opened={opened} onClose={onClose} title="Bulk import" size="lg">
			<Stack gap="sm">
				<Text size="sm" c="dimmed">
					One entry per line:
					<br />
					<Code>parameter_key,parameter_value,surface_form,language,polarity</Code>
					<br />
					Empty <Code>parameter_value</Code> is allowed for boolean params.
					Lines starting with <Code>#</Code> are skipped.
				</Text>
				<Textarea
					value={csv}
					onChange={(e) => setCsv(e.currentTarget.value)}
					placeholder="air_conditioner,,кондей,ru,positive"
					minRows={10}
					autosize
				/>
				<Group justify="flex-end">
					<Button variant="subtle" onClick={onClose}>
						Cancel
					</Button>
					<Button loading={busy} onClick={submit} disabled={!csv.trim()}>
						Import
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

export const AdminSynonyms = {
	route: "/admin/synonyms",
	Page,
};
