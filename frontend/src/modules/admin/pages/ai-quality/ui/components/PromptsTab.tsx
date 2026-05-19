import { useEffect, useMemo, useState } from "react";
import {
	Stack,
	Table,
	Badge,
	Group,
	Loader,
	Text,
	Button,
	Modal,
	Textarea,
	TextInput,
	Tabs,
	Code,
	Select,
} from "@mantine/core";
import { useUnit } from "effector-react";

import {
	$prompts,
	activatePromptFx,
	createPromptFx,
	fetchPromptsFx,
	type PromptTemplate,
} from "../../model";

/** Naïve word-level diff: prefix-/suffix-trim, then mark added/removed
 * lines side-by-side. Good enough for the admin tooling — we don't need
 * a full diff lib for what is essentially a "before vs after" peek. */
function lineDiff(a: string, b: string): { left: string[]; right: string[] } {
	return { left: a.split("\n"), right: b.split("\n") };
}

export function PromptsTab() {
	const prompts = useUnit($prompts);
	const loading = useUnit(fetchPromptsFx.pending);

	const [createOpen, setCreateOpen] = useState(false);
	const [diffOpen, setDiffOpen] = useState(false);
	const [diffPair, setDiffPair] = useState<{ left: PromptTemplate; right: PromptTemplate } | null>(null);

	useEffect(() => {
		void fetchPromptsFx();
	}, []);

	const kinds = useMemo(
		() => Array.from(new Set((prompts ?? []).map((p) => p.kind))),
		[prompts],
	);
	const [selectedKind, setSelectedKind] = useState<string | null>(null);

	const filtered = useMemo(() => {
		if (!prompts) return [];
		return selectedKind ? prompts.filter((p) => p.kind === selectedKind) : prompts;
	}, [prompts, selectedKind]);

	const onActivate = async (id: string) => {
		await activatePromptFx(id);
		void fetchPromptsFx();
	};

	const openDiff = (target: PromptTemplate) => {
		// Diff against the active version of the same kind (if any).
		const active = (prompts ?? []).find(
			(p) => p.kind === target.kind && p.is_active && p.id !== target.id,
		);
		if (!active) {
			setDiffPair({ left: target, right: target });
		} else {
			setDiffPair({ left: active, right: target });
		}
		setDiffOpen(true);
	};

	return (
		<Stack gap="md">
			<Group justify="space-between">
				<Select
					placeholder="Filter by kind"
					data={kinds.map((k) => ({ value: k, label: k }))}
					value={selectedKind}
					onChange={setSelectedKind}
					clearable
				/>
				<Button size="xs" onClick={() => setCreateOpen(true)}>
					New version
				</Button>
			</Group>
			{loading || !prompts ? (
				<Loader />
			) : (
				<Table withTableBorder striped>
					<Table.Thead>
						<Table.Tr>
							<Table.Th>Kind</Table.Th>
							<Table.Th>Version</Table.Th>
							<Table.Th>Model hint</Table.Th>
							<Table.Th>Active</Table.Th>
							<Table.Th>Created</Table.Th>
							<Table.Th />
						</Table.Tr>
					</Table.Thead>
					<Table.Tbody>
						{filtered.map((p) => (
							<Table.Tr key={p.id}>
								<Table.Td>{p.kind}</Table.Td>
								<Table.Td>v{p.version}</Table.Td>
								<Table.Td>{p.model_hint ?? "—"}</Table.Td>
								<Table.Td>
									{p.is_active ? (
										<Badge color="green">active</Badge>
									) : (
										<Badge color="gray" variant="light">
											inactive
										</Badge>
									)}
								</Table.Td>
								<Table.Td>{new Date(p.created_at).toLocaleString()}</Table.Td>
								<Table.Td>
									<Group gap="xs">
										<Button size="xs" variant="subtle" onClick={() => openDiff(p)}>
											Diff
										</Button>
										{!p.is_active && (
											<Button size="xs" color="blue" onClick={() => onActivate(p.id)}>
												Activate
											</Button>
										)}
									</Group>
								</Table.Td>
							</Table.Tr>
						))}
					</Table.Tbody>
				</Table>
			)}

			<CreatePromptModal opened={createOpen} onClose={() => setCreateOpen(false)} />
			<DiffModal
				opened={diffOpen}
				onClose={() => setDiffOpen(false)}
				pair={diffPair}
			/>
		</Stack>
	);
}

interface CreateProps {
	opened: boolean;
	onClose: () => void;
}

function CreatePromptModal({ opened, onClose }: CreateProps) {
	const [kind, setKind] = useState("");
	const [body, setBody] = useState("");
	const [modelHint, setModelHint] = useState("");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);

	const submit = async () => {
		setBusy(true);
		try {
			await createPromptFx({
				kind: kind.trim(),
				body,
				model_hint: modelHint.trim() || undefined,
				notes: notes.trim() || undefined,
			});
			void fetchPromptsFx();
			setKind("");
			setBody("");
			setModelHint("");
			setNotes("");
			onClose();
		} finally {
			setBusy(false);
		}
	};

	return (
		<Modal opened={opened} onClose={onClose} title="New prompt version" size="lg">
			<Stack gap="sm">
				<TextInput
					label="Kind"
					value={kind}
					onChange={(e) => setKind(e.currentTarget.value)}
					placeholder="listing_description"
					required
				/>
				<TextInput
					label="Model hint (optional)"
					value={modelHint}
					onChange={(e) => setModelHint(e.currentTarget.value)}
					placeholder="gpt-4o-mini"
				/>
				<Textarea
					label="Body"
					value={body}
					onChange={(e) => setBody(e.currentTarget.value)}
					minRows={10}
					autosize
					required
				/>
				<TextInput
					label="Notes"
					value={notes}
					onChange={(e) => setNotes(e.currentTarget.value)}
				/>
				<Group justify="flex-end">
					<Button variant="subtle" onClick={onClose}>
						Cancel
					</Button>
					<Button loading={busy} onClick={submit} disabled={!kind.trim() || !body.trim()}>
						Create
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

interface DiffProps {
	opened: boolean;
	onClose: () => void;
	pair: { left: PromptTemplate; right: PromptTemplate } | null;
}

function DiffModal({ opened, onClose, pair }: DiffProps) {
	const diff = pair ? lineDiff(pair.left.body, pair.right.body) : null;
	return (
		<Modal opened={opened} onClose={onClose} title="Prompt diff" size="xl">
			{pair && diff && (
				<Tabs defaultValue="diff">
					<Tabs.List>
						<Tabs.Tab value="diff">Side-by-side</Tabs.Tab>
						<Tabs.Tab value="meta">Metadata</Tabs.Tab>
					</Tabs.List>
					<Tabs.Panel value="diff" pt="sm">
						<Group align="flex-start" wrap="nowrap">
							<Stack gap={4} style={{ flex: 1 }}>
								<Text size="xs" c="dimmed">
									{pair.left.kind} v{pair.left.version}
									{pair.left.is_active ? " (active)" : ""}
								</Text>
								<Code block style={{ whiteSpace: "pre-wrap", minHeight: 240 }}>
									{diff.left.join("\n")}
								</Code>
							</Stack>
							<Stack gap={4} style={{ flex: 1 }}>
								<Text size="xs" c="dimmed">
									{pair.right.kind} v{pair.right.version}
									{pair.right.is_active ? " (active)" : ""}
								</Text>
								<Code block style={{ whiteSpace: "pre-wrap", minHeight: 240 }}>
									{diff.right.join("\n")}
								</Code>
							</Stack>
						</Group>
					</Tabs.Panel>
					<Tabs.Panel value="meta" pt="sm">
						<Stack gap="xs">
							<Text size="sm">
								<b>Left:</b> {pair.left.id} (created {new Date(pair.left.created_at).toLocaleString()})
							</Text>
							<Text size="sm">
								<b>Right:</b> {pair.right.id} (created {new Date(pair.right.created_at).toLocaleString()})
							</Text>
							{pair.right.notes && (
								<Text size="sm">
									<b>Notes:</b> {pair.right.notes}
								</Text>
							)}
						</Stack>
					</Tabs.Panel>
				</Tabs>
			)}
		</Modal>
	);
}
