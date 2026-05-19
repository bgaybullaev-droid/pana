import { useEffect, useState } from "react";
import {
	Stack,
	Table,
	Badge,
	Group,
	Pagination,
	Modal,
	Code,
	Loader,
	Text,
	TextInput,
	Select,
} from "@mantine/core";
import { useUnit } from "effector-react";

import {
	$generationDetail,
	$generations,
	fetchGenerationsFx,
	fetchGenerationDetailFx,
	type GenerationsQuery,
} from "../../model";

const OUTCOMES = ["ok", "fallback_template", "timeout", "rate_limit", "invalid_response"];

export function GenerationsTab() {
	const data = useUnit($generations);
	const loading = useUnit(fetchGenerationsFx.pending);
	const detail = useUnit($generationDetail);
	const detailLoading = useUnit(fetchGenerationDetailFx.pending);
	const [page, setPage] = useState(1);
	const [outcome, setOutcome] = useState<string | null>(null);
	const [model, setModel] = useState("");
	const [detailOpen, setDetailOpen] = useState(false);

	useEffect(() => {
		const q: GenerationsQuery = { page };
		if (outcome) q.outcome = outcome;
		if (model.trim()) q.model = model.trim();
		void fetchGenerationsFx(q);
	}, [page, outcome, model]);

	const openDetail = (id: string) => {
		setDetailOpen(true);
		void fetchGenerationDetailFx(id);
	};

	return (
		<Stack gap="md">
			<Group gap="sm">
				<Select
					placeholder="Outcome"
					data={[{ value: "", label: "Any" }, ...OUTCOMES.map((v) => ({ value: v, label: v }))]}
					value={outcome ?? ""}
					onChange={(v) => {
						setPage(1);
						setOutcome(v || null);
					}}
					clearable
				/>
				<TextInput
					placeholder="Model"
					value={model}
					onChange={(e) => {
						setPage(1);
						setModel(e.currentTarget.value);
					}}
				/>
			</Group>
			{loading || !data ? (
				<Loader />
			) : (
				<>
					<Table withTableBorder striped highlightOnHover>
						<Table.Thead>
							<Table.Tr>
								<Table.Th>Created</Table.Th>
								<Table.Th>Model</Table.Th>
								<Table.Th>Outcome</Table.Th>
								<Table.Th>Duration</Table.Th>
								<Table.Th>Cost</Table.Th>
								<Table.Th>Listing</Table.Th>
							</Table.Tr>
						</Table.Thead>
						<Table.Tbody>
							{data.items.map((row) => (
								<Table.Tr
									key={row.id}
									style={{ cursor: "pointer" }}
									onClick={() => openDetail(row.id)}
								>
									<Table.Td>{new Date(row.created_at).toLocaleString()}</Table.Td>
									<Table.Td>{row.model}</Table.Td>
									<Table.Td>
										<Badge color={row.outcome === "ok" ? "green" : "orange"}>
											{row.outcome}
										</Badge>
									</Table.Td>
									<Table.Td>{row.duration_ms} ms</Table.Td>
									<Table.Td>
										{row.cost_usd_micros != null
											? `$${(row.cost_usd_micros / 1_000_000).toFixed(4)}`
											: "—"}
									</Table.Td>
									<Table.Td>
										<Code>{row.listing_id ?? "—"}</Code>
									</Table.Td>
								</Table.Tr>
							))}
							{data.items.length === 0 && (
								<Table.Tr>
									<Table.Td colSpan={6}>
										<Text size="sm" c="dimmed" ta="center">
											No generations match the current filters.
										</Text>
									</Table.Td>
								</Table.Tr>
							)}
						</Table.Tbody>
					</Table>
					<Pagination
						value={page}
						onChange={setPage}
						total={Math.max(1, Math.ceil(data.total / 25))}
					/>
				</>
			)}

			<Modal
				opened={detailOpen}
				onClose={() => setDetailOpen(false)}
				size="xl"
				title={detail ? `Generation ${detail.id}` : "Generation"}
			>
				{detailLoading || !detail ? (
					<Loader />
				) : (
					<Stack gap="sm">
						<Group gap="md">
							<Text size="sm">
								<b>Model:</b> {detail.model}
							</Text>
							<Text size="sm">
								<b>Outcome:</b> {detail.outcome}
							</Text>
							<Text size="sm">
								<b>Duration:</b> {detail.duration_ms} ms
							</Text>
						</Group>
						<div>
							<Text fw={600} size="sm" mb={4}>
								Prompt
							</Text>
							<Code block style={{ maxHeight: 280, overflow: "auto", whiteSpace: "pre-wrap" }}>
								{detail.prompt_text}
							</Code>
						</div>
						<div>
							<Text fw={600} size="sm" mb={4}>
								Response
							</Text>
							<Code block style={{ maxHeight: 280, overflow: "auto", whiteSpace: "pre-wrap" }}>
								{detail.response_text}
							</Code>
						</div>
					</Stack>
				)}
			</Modal>
		</Stack>
	);
}
