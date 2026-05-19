/**
 * Block phase-2 — admin banners CRUD console.
 *
 * Table of banners + create/edit modal + activate-toggle action. Image
 * URL is a plain text field for v1 — admin pastes a CDN URL.
 */

import { useEffect, useState } from "react";
import {
	Container,
	Stack,
	Title,
	Text,
	Group,
	Button,
	Table,
	Badge,
	Modal,
	TextInput,
	Select,
	Switch,
	ActionIcon,
	Loader,
	Image,
	Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconPlus,
	IconPencil,
	IconTrash,
	IconExternalLink,
	IconEye,
	IconClick,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import {
	$banners,
	createBannerFx,
	deleteBannerFx,
	fetchBannersFx,
	updateBannerFx,
	type Banner,
	type BannerCreate,
	type BannerLanguage,
	type BannerPlacement,
} from "../../model";

const PLACEMENTS: BannerPlacement[] = ["home_top", "home_inline", "listing_inline"];
const LANGUAGES: BannerLanguage[] = ["*", "ru", "uz", "uz_cyrl"];

interface FormState {
	id?: string;
	title: string;
	image_url: string;
	target_url: string;
	placement: BannerPlacement;
	language: BannerLanguage;
	is_active: boolean;
}

function emptyForm(): FormState {
	return {
		title: "",
		image_url: "",
		target_url: "",
		placement: "home_top",
		language: "*",
		is_active: true,
	};
}

function Page() {
	const banners = useUnit($banners);
	const loading = useUnit(fetchBannersFx.pending);
	const { t } = useTranslation("admin");
	const [open, setOpen] = useState(false);
	const [form, setForm] = useState<FormState>(emptyForm());

	useEffect(() => {
		void fetchBannersFx();
	}, []);

	const openCreate = () => {
		setForm(emptyForm());
		setOpen(true);
	};

	const openEdit = (banner: Banner) => {
		setForm({
			id: banner.id,
			title: banner.title,
			image_url: banner.image_url,
			target_url: banner.target_url,
			placement: banner.placement,
			language: banner.language,
			is_active: banner.is_active,
		});
		setOpen(true);
	};

	const handleSubmit = async () => {
		if (!form.title || !form.image_url || !form.target_url) {
			notifications.show({
				color: "red",
				message: t("banners.validationRequired", {
					defaultValue: "Title / image / target are required",
				}),
			});
			return;
		}
		const body: BannerCreate = {
			title: form.title,
			image_url: form.image_url,
			target_url: form.target_url,
			placement: form.placement,
			language: form.language,
			is_active: form.is_active,
		};
		try {
			if (form.id) {
				await updateBannerFx({ id: form.id, body });
			} else {
				await createBannerFx(body);
			}
			setOpen(false);
		} catch (err) {
			notifications.show({
				color: "red",
				message: (err as Error)?.message || "Failed",
			});
		}
	};

	const handleToggleActive = async (banner: Banner) => {
		await updateBannerFx({
			id: banner.id,
			body: { is_active: !banner.is_active },
		});
	};

	const handleDelete = async (id: string) => {
		if (!window.confirm(t("banners.confirmDelete", { defaultValue: "Deactivate banner?" }))) {
			return;
		}
		await deleteBannerFx(id);
	};

	const placementLabel = (p: BannerPlacement) => {
		const map: Record<BannerPlacement, string> = {
			home_top: t("banners.placement.homeTop"),
			home_inline: t("banners.placement.homeInline"),
			listing_inline: t("banners.placement.listingInline"),
		};
		return map[p];
	};

	return (
		<Container size={1200} py="md">
			<Stack gap="sm" mb="md">
				<Group justify="space-between">
					<Title order={2}>{t("banners.title")}</Title>
					<Button leftSection={<IconPlus size={14} />} onClick={openCreate}>
						{t("banners.create")}
					</Button>
				</Group>
				<Text size="sm" c="dimmed">
					{t("banners.subtitle", {
						defaultValue:
							"Marketing banners shown on the buyer home page and listing detail.",
					})}
				</Text>
			</Stack>

			{loading ? (
				<Loader />
			) : (
				<Table withTableBorder striped highlightOnHover>
					<Table.Thead>
						<Table.Tr>
							<Table.Th>{t("banners.colImage", { defaultValue: "Image" })}</Table.Th>
							<Table.Th>{t("banners.colTitle", { defaultValue: "Title" })}</Table.Th>
							<Table.Th>{t("banners.colPlacement", { defaultValue: "Placement" })}</Table.Th>
							<Table.Th>{t("banners.colLang", { defaultValue: "Lang" })}</Table.Th>
							<Table.Th>{t("banners.colStats", { defaultValue: "Stats" })}</Table.Th>
							<Table.Th>{t("banners.colActive", { defaultValue: "Active" })}</Table.Th>
							<Table.Th />
						</Table.Tr>
					</Table.Thead>
					<Table.Tbody>
						{banners.map((b) => (
							<Table.Tr key={b.id}>
								<Table.Td>
									<Image
										src={b.image_url}
										alt={b.title}
										w={60}
										h={36}
										fit="cover"
										radius="sm"
										fallbackSrc="https://placehold.co/60x36?text=N/A"
									/>
								</Table.Td>
								<Table.Td>
									<Stack gap={2}>
										<Text size="sm" fw={600}>{b.title}</Text>
										<Tooltip label={b.target_url}>
											<Text size="xs" c="dimmed" truncate maw={240}>
												<IconExternalLink size={10} /> {b.target_url}
											</Text>
										</Tooltip>
									</Stack>
								</Table.Td>
								<Table.Td>
									<Badge size="sm" variant="light">
										{placementLabel(b.placement)}
									</Badge>
								</Table.Td>
								<Table.Td>
									<Badge size="sm" variant="outline">
										{b.language}
									</Badge>
								</Table.Td>
								<Table.Td>
									<Group gap={6} wrap="nowrap">
										<Tooltip label="impressions">
											<Group gap={2}>
												<IconEye size={12} />
												<Text size="xs">{b.impressions}</Text>
											</Group>
										</Tooltip>
										<Tooltip label="clicks">
											<Group gap={2}>
												<IconClick size={12} />
												<Text size="xs">{b.clicks}</Text>
											</Group>
										</Tooltip>
									</Group>
								</Table.Td>
								<Table.Td>
									<Switch
										checked={b.is_active}
										onChange={() => handleToggleActive(b)}
									/>
								</Table.Td>
								<Table.Td>
									<Group gap={4}>
										<ActionIcon variant="subtle" onClick={() => openEdit(b)}>
											<IconPencil size={14} />
										</ActionIcon>
										<ActionIcon
											variant="subtle"
											color="red"
											onClick={() => handleDelete(b.id)}
										>
											<IconTrash size={14} />
										</ActionIcon>
									</Group>
								</Table.Td>
							</Table.Tr>
						))}
					</Table.Tbody>
				</Table>
			)}

			<Modal
				opened={open}
				onClose={() => setOpen(false)}
				title={
					<Text fw={700}>
						{form.id ? t("banners.edit") : t("banners.create")}
					</Text>
				}
				centered
				radius="md"
			>
				<Stack gap="sm">
					<TextInput
						label={t("banners.fieldTitle", { defaultValue: "Title" })}
						value={form.title}
						onChange={(e) =>
							setForm((p) => ({ ...p, title: e.currentTarget.value }))
						}
						required
					/>
					<TextInput
						label={t("banners.fieldImageUrl", { defaultValue: "Image URL" })}
						placeholder="https://cdn.example.com/banner.jpg"
						value={form.image_url}
						onChange={(e) =>
							setForm((p) => ({ ...p, image_url: e.currentTarget.value }))
						}
						required
					/>
					<TextInput
						label={t("banners.fieldTargetUrl", { defaultValue: "Target URL" })}
						placeholder="https://example.com/promo"
						value={form.target_url}
						onChange={(e) =>
							setForm((p) => ({ ...p, target_url: e.currentTarget.value }))
						}
						required
					/>
					<Select
						label={t("banners.fieldPlacement", { defaultValue: "Placement" })}
						data={PLACEMENTS.map((p) => ({
							value: p,
							label: placementLabel(p),
						}))}
						value={form.placement}
						onChange={(v) =>
							v &&
							setForm((p) => ({ ...p, placement: v as BannerPlacement }))
						}
					/>
					<Select
						label={t("banners.fieldLanguage", { defaultValue: "Language" })}
						data={LANGUAGES.map((l) => ({ value: l, label: l }))}
						value={form.language}
						onChange={(v) =>
							v && setForm((p) => ({ ...p, language: v as BannerLanguage }))
						}
					/>
					<Switch
						label={t("banners.fieldActive", { defaultValue: "Active" })}
						checked={form.is_active}
						onChange={(e) =>
							setForm((p) => ({ ...p, is_active: e.currentTarget.checked }))
						}
					/>
					<Group justify="flex-end" gap="sm" mt="sm">
						<Button variant="default" onClick={() => setOpen(false)}>
							{t("common.cancel")}
						</Button>
						<Button onClick={handleSubmit}>{t("common.apply")}</Button>
					</Group>
				</Stack>
			</Modal>
		</Container>
	);
}

export const AdminBanners = { Page };
