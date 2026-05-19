/**
 * Block F V2.0 (F4b) — Cabinet paywall modal.
 *
 * Shown when ``GET /seller/exports/...`` returns 402. CTA navigates
 * to the existing seller tariffs page (Block C C1).
 */

import { Modal, Stack, Text, Button, Group } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface PaywallModalProps {
	opened: boolean;
	onClose: () => void;
}

export function PaywallModal({ opened, onClose }: PaywallModalProps) {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();

	return (
		<Modal
			opened={opened}
			onClose={onClose}
			title={t("textExport.paywallTitle", "Подписка Кабинет")}
			centered
		>
			<Stack gap="md">
				<Text size="sm">
					{t(
						"textExport.paywallBody",
						"Экспорт в OLX / Telegram / Instagram доступен с подпиской «Кабинет». 99 000 сум в месяц.",
					)}
				</Text>
				<Group justify="flex-end" gap="sm">
					<Button variant="subtle" onClick={onClose}>
						{t("textExport.paywallCancel", "Не сейчас")}
					</Button>
					<Button
						color="blue"
						onClick={() => {
							onClose();
							navigate("/seller/tariffs");
						}}
					>
						{t("textExport.paywallSubscribe", "Подписаться")}
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
