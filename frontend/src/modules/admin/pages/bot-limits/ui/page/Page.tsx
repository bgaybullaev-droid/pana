/**
 * Block D (FU3) — admin console for the bot rate limits.
 *
 * Edits the singleton settings row that throttles the two spammy bot
 * surfaces (in-chat search + Inline Mode) and the "too many requests"
 * message shown to users. Numbers + toggles per surface; the message is
 * pre-filled in all three bot locales and cannot be left blank.
 */

import { useEffect, useState } from "react";
import {
	Button,
	Card,
	Container,
	Group,
	Loader,
	NumberInput,
	Stack,
	Switch,
	Text,
	Textarea,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";

import {
	$botLimits,
	fetchBotLimitsFx,
	saveBotLimitsFx,
	type BotRateLimitSettings,
} from "../../model";

function Page() {
	const settings = useUnit($botLimits);
	const loading = useUnit(fetchBotLimitsFx.pending);
	const saving = useUnit(saveBotLimitsFx.pending);
	const { t } = useTranslation("admin");
	const [form, setForm] = useState<BotRateLimitSettings | null>(null);

	useEffect(() => {
		void fetchBotLimitsFx();
	}, []);

	useEffect(() => {
		if (settings) setForm(settings);
	}, [settings]);

	if (loading || !form) {
		return (
			<Container size={720} py="md">
				<Loader />
			</Container>
		);
	}

	const set = <K extends keyof BotRateLimitSettings>(
		key: K,
		value: BotRateLimitSettings[K],
	) => setForm((f) => (f ? { ...f, [key]: value } : f));

	const messagesEmpty =
		!form.limit_message_ru.trim() ||
		!form.limit_message_uz.trim() ||
		!form.limit_message_uz_cyrl.trim();

	const onSave = async () => {
		try {
			await saveBotLimitsFx({
				search_enabled: form.search_enabled,
				search_limit: form.search_limit,
				search_window_sec: form.search_window_sec,
				inline_enabled: form.inline_enabled,
				inline_limit: form.inline_limit,
				inline_window_sec: form.inline_window_sec,
				limit_message_ru: form.limit_message_ru,
				limit_message_uz: form.limit_message_uz,
				limit_message_uz_cyrl: form.limit_message_uz_cyrl,
			});
			notifications.show({ message: t("botLimits.saved"), color: "green" });
		} catch {
			notifications.show({ message: t("botLimits.saveError"), color: "red" });
		}
	};

	return (
		<Container size={720} py="md">
			<Stack gap="sm" mb="md">
				<Title order={2}>{t("botLimits.title")}</Title>
				<Text size="sm" c="dimmed">
					{t("botLimits.subtitle")}
				</Text>
			</Stack>

			<Stack gap="lg">
				<Card withBorder padding="md">
					<Stack gap="sm">
						<Group justify="space-between">
							<Text fw={600}>{t("botLimits.searchSection")}</Text>
							<Switch
								checked={form.search_enabled}
								onChange={(e) => set("search_enabled", e.currentTarget.checked)}
								label={t("botLimits.enabled")}
							/>
						</Group>
						<Group grow>
							<NumberInput
								label={t("botLimits.limit")}
								min={1}
								max={10000}
								value={form.search_limit}
								onChange={(v) => set("search_limit", Number(v) || 1)}
								disabled={!form.search_enabled}
							/>
							<NumberInput
								label={t("botLimits.window")}
								min={1}
								max={3600}
								value={form.search_window_sec}
								onChange={(v) => set("search_window_sec", Number(v) || 1)}
								disabled={!form.search_enabled}
							/>
						</Group>
					</Stack>
				</Card>

				<Card withBorder padding="md">
					<Stack gap="sm">
						<Group justify="space-between">
							<Text fw={600}>{t("botLimits.inlineSection")}</Text>
							<Switch
								checked={form.inline_enabled}
								onChange={(e) => set("inline_enabled", e.currentTarget.checked)}
								label={t("botLimits.enabled")}
							/>
						</Group>
						<Group grow>
							<NumberInput
								label={t("botLimits.limit")}
								min={1}
								max={10000}
								value={form.inline_limit}
								onChange={(v) => set("inline_limit", Number(v) || 1)}
								disabled={!form.inline_enabled}
							/>
							<NumberInput
								label={t("botLimits.window")}
								min={1}
								max={3600}
								value={form.inline_window_sec}
								onChange={(v) => set("inline_window_sec", Number(v) || 1)}
								disabled={!form.inline_enabled}
							/>
						</Group>
					</Stack>
				</Card>

				<Card withBorder padding="md">
					<Stack gap="sm">
						<Text fw={600}>{t("botLimits.messageSection")}</Text>
						<Text size="xs" c="dimmed">
							{t("botLimits.messageHint")}
						</Text>
						<Textarea
							label="RU"
							autosize
							minRows={2}
							value={form.limit_message_ru}
							onChange={(e) => set("limit_message_ru", e.currentTarget.value)}
						/>
						<Textarea
							label="UZ"
							autosize
							minRows={2}
							value={form.limit_message_uz}
							onChange={(e) => set("limit_message_uz", e.currentTarget.value)}
						/>
						<Textarea
							label="UZ (cyrl)"
							autosize
							minRows={2}
							value={form.limit_message_uz_cyrl}
							onChange={(e) =>
								set("limit_message_uz_cyrl", e.currentTarget.value)
							}
						/>
					</Stack>
				</Card>

				<Group justify="flex-end">
					<Button
						leftSection={<IconDeviceFloppy size={16} />}
						loading={saving}
						onClick={onSave}
						disabled={messagesEmpty}
					>
						{t("botLimits.save")}
					</Button>
				</Group>
			</Stack>
		</Container>
	);
}

export const AdminBotLimits = {
	route: "/admin/bot-limits",
	Page,
};
