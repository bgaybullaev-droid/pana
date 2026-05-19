/**
 * Phase-2 seller CRM page.
 *
 * Pipeline-grouped client list. Each card carries name / phone /
 * notes and a stage dropdown to move it across the 6 pipeline
 * stages. Drag-and-drop is intentionally descoped from v1 since
 * `@hello-pangea/dnd` is not in deps — the dropdown gives the
 * same UX with one fewer click than a modal would.
 */

import { useEffect, useState } from "react";
import {
	Badge,
	Button,
	Card,
	Container,
	Group,
	Loader,
	Modal,
	Select,
	SimpleGrid,
	Stack,
	Text,
	TextInput,
	Textarea,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import { InnerPage } from "@shared/ui/InnerPage";
import {
	$clients,
	PIPELINE_STAGES,
	type PipelineStage,
	type SellerClient,
	createClientFx,
	deleteClientFx,
	fetchClientsFx,
	updateClientFx,
} from "../../model";

function Page() {
	const { t } = useTranslation("seller");
	const clients = useUnit($clients);
	const loading = useUnit(fetchClientsFx.pending);
	const [createOpen, setCreateOpen] = useState(false);
	const [editTarget, setEditTarget] = useState<SellerClient | null>(null);

	useEffect(() => {
		void fetchClientsFx();
	}, []);

	const byStage = (stage: PipelineStage) =>
		clients.filter((c) => c.pipeline_stage === stage);

	const onChangeStage = async (client: SellerClient, stage: PipelineStage) => {
		await updateClientFx({ id: client.id, pipeline_stage: stage }).catch(
			() => {
				notifications.show({
					color: "red",
					message: "Failed to change stage",
				});
			},
		);
	};

	const onDelete = async (id: string) => {
		await deleteClientFx(id);
		await fetchClientsFx();
	};

	return (
		<InnerPage title={t("clients.title")} noPadding>
			<Container size="lg" px="md" py="md">
				<Stack gap="md">
					<Group justify="space-between" align="center">
						<Title order={3}>{t("clients.title")}</Title>
						<Button
							leftSection={<IconPlus size={14} />}
							onClick={() => setCreateOpen(true)}
						>
							{t("clients.new")}
						</Button>
					</Group>
					{loading && clients.length === 0 ? (
						<Loader />
					) : clients.length === 0 ? (
						<Text c="dimmed" ta="center" py="xl">
							{t("clients.empty")}
						</Text>
					) : (
						<SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
							{PIPELINE_STAGES.map((stage) => (
								<Card key={stage} withBorder padding="sm" radius="md">
									<Group justify="space-between" mb="xs">
										<Badge size="md" variant="light">
											{t(`clients.pipeline.${stage}`)}
										</Badge>
										<Text size="xs" c="dimmed">
											{byStage(stage).length}
										</Text>
									</Group>
									<Stack gap="xs">
										{byStage(stage).map((client) => (
											<Card
												key={client.id}
												withBorder
												padding="xs"
												radius="sm"
												style={{ cursor: "pointer" }}
												onClick={() => setEditTarget(client)}
											>
												<Group justify="space-between" wrap="nowrap">
													<Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
														<Text fw={600} size="sm" truncate>
															{client.name}
														</Text>
														{client.phone && (
															<Text size="xs" c="dimmed" truncate>
																{client.phone}
															</Text>
														)}
													</Stack>
													<Select
														size="xs"
														w={120}
														value={client.pipeline_stage}
														onClick={(e) => e.stopPropagation()}
														data={PIPELINE_STAGES.map((s) => ({
															value: s,
															label: t(`clients.pipeline.${s}`),
														}))}
														onChange={(v) =>
															v &&
															onChangeStage(client, v as PipelineStage)
														}
													/>
												</Group>
											</Card>
										))}
										{byStage(stage).length === 0 && (
											<Text size="xs" c="dimmed" ta="center" py="sm">
												—
											</Text>
										)}
									</Stack>
								</Card>
							))}
						</SimpleGrid>
					)}
				</Stack>
			</Container>
			<CreateModal
				opened={createOpen}
				onClose={() => setCreateOpen(false)}
				onDone={() => fetchClientsFx()}
			/>
			<EditModal
				client={editTarget}
				onClose={() => setEditTarget(null)}
				onDelete={onDelete}
			/>
		</InnerPage>
	);
}

interface CreateProps {
	opened: boolean;
	onClose: () => void;
	onDone: () => void;
}

function CreateModal({ opened, onClose, onDone }: CreateProps) {
	const { t } = useTranslation("seller");
	const [name, setName] = useState("");
	const [phone, setPhone] = useState("");
	const [notes, setNotes] = useState("");
	const [stage, setStage] = useState<PipelineStage>("new");
	const [busy, setBusy] = useState(false);

	const reset = () => {
		setName("");
		setPhone("");
		setNotes("");
		setStage("new");
	};

	const submit = async () => {
		if (!name.trim()) return;
		setBusy(true);
		try {
			await createClientFx({
				name: name.trim(),
				phone: phone.trim() || undefined,
				notes: notes.trim() || undefined,
				pipeline_stage: stage,
			});
			reset();
			onDone();
			onClose();
		} catch {
			notifications.show({
				color: "red",
				message: "Failed to create client",
			});
		} finally {
			setBusy(false);
		}
	};

	return (
		<Modal
			opened={opened}
			onClose={() => {
				onClose();
				reset();
			}}
			title={t("clients.new")}
			centered
		>
			<Stack gap="sm">
				<TextInput
					label={t("clients.fieldName")}
					value={name}
					onChange={(e) => setName(e.currentTarget.value)}
					required
				/>
				<TextInput
					label={t("clients.fieldPhone")}
					value={phone}
					onChange={(e) => setPhone(e.currentTarget.value)}
				/>
				<Textarea
					label={t("clients.fieldNotes")}
					value={notes}
					onChange={(e) => setNotes(e.currentTarget.value)}
					autosize
					minRows={2}
				/>
				<Select
					label={t("clients.fieldStage")}
					value={stage}
					data={PIPELINE_STAGES.map((s) => ({
						value: s,
						label: t(`clients.pipeline.${s}`),
					}))}
					onChange={(v) => v && setStage(v as PipelineStage)}
				/>
				<Group justify="flex-end" mt="xs">
					<Button variant="subtle" onClick={onClose}>
						{t("clients.cancel")}
					</Button>
					<Button onClick={submit} loading={busy} disabled={!name.trim()}>
						{t("clients.save")}
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}

interface EditProps {
	client: SellerClient | null;
	onClose: () => void;
	onDelete: (id: string) => void;
}

function EditModal({ client, onClose, onDelete }: EditProps) {
	const { t } = useTranslation("seller");
	const [name, setName] = useState("");
	const [phone, setPhone] = useState("");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);

	useEffect(() => {
		if (client) {
			setName(client.name);
			setPhone(client.phone ?? "");
			setNotes(client.notes ?? "");
		}
	}, [client]);

	if (!client) return null;

	const save = async () => {
		setBusy(true);
		try {
			await updateClientFx({
				id: client.id,
				name: name.trim() || undefined,
				phone: phone.trim() || undefined,
				notes: notes.trim() || undefined,
			});
			onClose();
		} catch {
			notifications.show({
				color: "red",
				message: "Failed to save",
			});
		} finally {
			setBusy(false);
		}
	};

	return (
		<Modal
			opened={!!client}
			onClose={onClose}
			title={client.name}
			centered
		>
			<Stack gap="sm">
				<TextInput
					label={t("clients.fieldName")}
					value={name}
					onChange={(e) => setName(e.currentTarget.value)}
				/>
				<TextInput
					label={t("clients.fieldPhone")}
					value={phone}
					onChange={(e) => setPhone(e.currentTarget.value)}
				/>
				<Textarea
					label={t("clients.fieldNotes")}
					value={notes}
					onChange={(e) => setNotes(e.currentTarget.value)}
					autosize
					minRows={3}
				/>
				<Group justify="space-between" mt="xs">
					<Button
						color="red"
						variant="subtle"
						leftSection={<IconTrash size={14} />}
						onClick={() => {
							onDelete(client.id);
							onClose();
						}}
					>
						{t("clients.delete")}
					</Button>
					<Group>
						<Button variant="subtle" onClick={onClose}>
							{t("clients.cancel")}
						</Button>
						<Button onClick={save} loading={busy}>
							{t("clients.save")}
						</Button>
					</Group>
				</Group>
			</Stack>
		</Modal>
	);
}

export const SellerClients = {
	route: "/seller/clients",
	Page,
};
