/**
 * Block F V2.0 (F4b) — text export buttons block.
 *
 * Mounted under the listing detail card (and after publish on
 * Stage 2). 4 buttons, one per output: OLX / Telegram / Instagram /
 * Пакет. Each button:
 *
 *   - POSTs ``GET /seller/exports/{id}/{platform}?lang=…``.
 *   - On 200: writes to clipboard + toast.
 *   - On 402: opens the paywall modal.
 *   - On 422: toasts "AI text not ready" / "template not configured".
 */

import { useState } from "react";
import { Button, Group, Text, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconBrandTelegram,
	IconBrandInstagram,
	IconPackages,
	IconExternalLink,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import {
	fetchExportFx,
	type ExportPackResponse,
	type ExportPlatform,
	type ExportResponse,
} from "../model";
import { PaywallModal } from "./PaywallModal";

interface ExportButtonsProps {
	listingId: string;
	/** Listing's primary AI-text language (defaults to ``ru``). */
	lang?: string;
}

const PLATFORMS: { value: ExportPlatform; labelKey: string; defaultLabel: string; icon: React.ReactNode }[] = [
	{ value: "olx", labelKey: "textExport.platforms.olx", defaultLabel: "OLX", icon: <IconExternalLink size={14} /> },
	{
		value: "telegram_channel",
		labelKey: "textExport.platforms.telegram",
		defaultLabel: "Telegram-канал",
		icon: <IconBrandTelegram size={14} />,
	},
	{
		value: "instagram",
		labelKey: "textExport.platforms.instagram",
		defaultLabel: "Instagram",
		icon: <IconBrandInstagram size={14} />,
	},
	{ value: "pack", labelKey: "textExport.platforms.pack", defaultLabel: "Пакет", icon: <IconPackages size={14} /> },
];

function isPack(data: ExportResponse | ExportPackResponse): data is ExportPackResponse {
	return "items" in data;
}

export function ExportButtons({ listingId, lang = "ru" }: ExportButtonsProps) {
	const { t } = useTranslation("seller");
	const [paywall, setPaywall] = useState(false);
	const [busy, setBusy] = useState<ExportPlatform | null>(null);

	const handleClick = async (platform: ExportPlatform) => {
		setBusy(platform);
		try {
			const data = await fetchExportFx({ listingId, platform, lang });
			let clipboardText = "";
			if (isPack(data)) {
				clipboardText = data.items
					.map((i) => `── ${i.platform} ──\n${i.title ? i.title + "\n\n" : ""}${i.text}`)
					.join("\n\n");
			} else {
				clipboardText = data.title ? `${data.title}\n\n${data.text}` : data.text;
			}
			await navigator.clipboard.writeText(clipboardText);
			notifications.show({
				title: t("textExport.copiedTitle", "Скопировано"),
				message: t(
					"textExport.copiedBody",
					"Вставьте текст в нужное приложение.",
				),
				color: "green",
			});
		} catch (err: unknown) {
			const status = (err as { response?: { status?: number } })?.response?.status;
			const detail = (
				err as {
					response?: { data?: { detail?: { error?: string } } };
				}
			)?.response?.data?.detail;
			if (status === 402) {
				setPaywall(true);
			} else if (status === 422) {
				const code = detail?.error ?? "";
				notifications.show({
					title: t("textExport.errorTitle", "Не удалось экспортировать"),
					message:
						code === "ai_text_not_ready"
							? t(
									"textExport.aiNotReady",
									"AI описание ещё не готово. Опубликуйте после генерации текста.",
								)
							: code === "template_not_configured"
								? t(
										"textExport.templateMissing",
										"Шаблон ещё не настроен. Свяжитесь с поддержкой.",
									)
								: t("textExport.errorGeneric", "Попробуйте ещё раз."),
					color: "red",
				});
			} else {
				notifications.show({
					title: t("textExport.errorTitle", "Не удалось экспортировать"),
					message: t("textExport.errorGeneric", "Попробуйте ещё раз."),
					color: "red",
				});
			}
		} finally {
			setBusy(null);
		}
	};

	return (
		<Stack gap="xs">
			<Text size="xs" c="dimmed">
				{t("textExport.heading", "Экспорт текста")}
			</Text>
			<Group gap="xs">
				{PLATFORMS.map((p) => (
					<Button
						key={p.value}
						size="xs"
						variant="light"
						leftSection={p.icon}
						loading={busy === p.value}
						onClick={() => handleClick(p.value)}
					>
						{t(p.labelKey, p.defaultLabel)}
					</Button>
				))}
			</Group>
			<PaywallModal opened={paywall} onClose={() => setPaywall(false)} />
		</Stack>
	);
}
