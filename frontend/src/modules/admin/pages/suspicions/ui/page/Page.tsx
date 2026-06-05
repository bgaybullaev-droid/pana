/**
 * Phase-2 admin suspicions queue.
 *
 * Tabular list filterable by status + signal_kind. Clicking a row
 * opens a side drawer showing the raw evidence JSON and three
 * decision buttons (merge / dismiss / reviewed) plus a freeform
 * notes textarea — all wired to ``POST /admin/suspicions/:id/decide``.
 */

import { useEffect, useState } from "react";
import {
	Badge,
	Button,
	Code,
	Container,
	Drawer,
	Group,
	Loader,
	Select,
	Stack,
	Table,
	Text,
	Textarea,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import {
	$suspicions,
	type Suspicion,
	type SuspicionDecision,
	type SuspicionStatus,
	decideSuspicionFx,
	fetchSuspicionsFx,
} from "../../model";

const STATUSES: SuspicionStatus[] = ["open", "reviewed", "dismissed", "merged"];
const SIGNAL_KINDS = ["", "phone_collision", "similar_names"];

function Page() {
	const { t } = useTranslation("admin");
	const rows = useUnit($suspicions);
	const loading = useUnit(fetchSuspicionsFx.pending);
	const [statusFilter, setStatusFilter] = useState<SuspicionStatus>("open");
	const [signalKind, setSignalKind] = useState<string>("");
	const [selected, setSelected] = useState<Suspicion | null>(null);

	useEffect(() => {
		void fetchSuspicionsFx({
			status: statusFilter,
			signal_kind: signalKind || undefined,
		});
	}, [statusFilter, signalKind]);

	const refresh = () =>
		fetchSuspicionsFx({
			status: statusFilter,
			signal_kind: signalKind || undefined,
		});

	const signalLabel = (kind: string): string => {
		if (kind === "phone_collision")
			return t("suspicions.signalKind.phoneCollision");
		if (kind === "similar_names")
			return t("suspicions.signalKind.similarNames");
		return kind;
	};

	return (
		<Container size={1200} py="md">
			<Stack gap="sm" mb="md">
				<Title order={2}>{t("suspicions.title")}</Title>
			</Stack>
			<Group gap="sm" mb="md">
				<Select
					value={statusFilter}
					onChange={(v) => v && setStatusFilter(v as SuspicionStatus)}
					data={STATUSES.map((s) => ({ value: s, label: s }))}
				/>
				<Select
					value={signalKind}
					onChange={(v) => setSignalKind(v ?? "")}
					data={SIGNAL_KINDS.map((k) => ({
						value: k,
						label: k || "all",
					}))}
				/>
			</Group>
			{loading || !rows ? (
				<Loader />
			) : (
				<Table withTableBorder striped highlightOnHover>
					<Table.Thead>
						<Table.Tr>
							<Table.Th>Signal</Table.Th>
							<Table.Th>Primary user</Table.Th>
							<Table.Th>Status</Table.Th>
							<Table.Th>Created</Table.Th>
						</Table.Tr>
					</Table.Thead>
					<Table.Tbody>
						{rows.map((r) => (
							<Table.Tr
								key={r.id}
								style={{ cursor: "pointer" }}
								onClick={() => setSelected(r)}
							>
								<Table.Td>
									<Badge variant="light">{signalLabel(r.signal_kind)}</Badge>
								</Table.Td>
								<Table.Td>
									<Code>{r.primary_user_id.slice(0, 8)}</Code>
								</Table.Td>
								<Table.Td>
									<Badge
										color={
											r.status === "open"
												? "orange"
												: r.status === "merged"
													? "red"
													: r.status === "dismissed"
														? "gray"
														: "blue"
										}
										variant="filled"
										size="sm"
									>
										{r.status}
									</Badge>
								</Table.Td>
								<Table.Td>
									<Text size="xs" c="dimmed">
										{new Date(r.created_at).toLocaleString()}
									</Text>
								</Table.Td>
							</Table.Tr>
						))}
						{rows.length === 0 && (
							<Table.Tr>
								<Table.Td colSpan={4}>
									<Text size="sm" c="dimmed" ta="center">
										—
									</Text>
								</Table.Td>
							</Table.Tr>
						)}
					</Table.Tbody>
				</Table>
			)}
			<DecideDrawer
				suspicion={selected}
				onClose={() => setSelected(null)}
				onDone={() => {
					setSelected(null);
					void refresh();
				}}
			/>
		</Container>
	);
}

interface DecideProps {
	suspicion: Suspicion | null;
	onClose: () => void;
	onDone: () => void;
}

function DecideDrawer({ suspicion, onClose, onDone }: DecideProps) {
	const { t } = useTranslation("admin");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);

	useEffect(() => {
		setNotes(suspicion?.notes ?? "");
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [suspicion?.id]);

	const decide = async (decision: SuspicionDecision) => {
		if (!suspicion) return;
		setBusy(true);
		try {
			await decideSuspicionFx({
				id: suspicion.id,
				decision,
				notes: notes.trim() || undefined,
			});
			notifications.show({ color: "green", message: `Marked ${decision}` });
			onDone();
		} catch {
			notifications.show({ color: "red", message: "Decision failed" });
		} finally {
			setBusy(false);
		}
	};

	return (
		<Drawer
			opened={!!suspicion}
			onClose={onClose}
			title={t("suspicions.title")}
			position="right"
			size="md"
		>
			{suspicion && (
				<Stack gap="md">
					<Group justify="space-between">
						<Badge variant="light">{suspicion.signal_kind}</Badge>
						<Badge>{suspicion.status}</Badge>
					</Group>
					<Stack gap={4}>
						<Text size="sm" fw={600}>
							{t("suspicions.evidence")}
						</Text>
						<Code block>
							{JSON.stringify(suspicion.evidence, null, 2)}
						</Code>
					</Stack>
					<Textarea
						label="Notes"
						value={notes}
						onChange={(e) => setNotes(e.currentTarget.value)}
						autosize
						minRows={3}
					/>
					<Group grow>
						<Button
							color="red"
							loading={busy}
							onClick={() => decide("merged")}
						>
							{t("suspicions.decide.merge")}
						</Button>
						<Button
							color="gray"
							loading={busy}
							onClick={() => decide("dismissed")}
						>
							{t("suspicions.decide.dismiss")}
						</Button>
						<Button
							color="blue"
							loading={busy}
							onClick={() => decide("reviewed")}
						>
							{t("suspicions.decide.review")}
						</Button>
					</Group>
				</Stack>
			)}
		</Drawer>
	);
}

export const AdminSuspicions = {
	route: "/admin/suspicions",
	Page,
};
