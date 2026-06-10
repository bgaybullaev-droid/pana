import { useEffect, useState } from "react";
import {
	Box,
	Button,
	Card,
	Group,
	Modal,
	Select,
	Skeleton,
	Stack,
	Text,
	TextInput,
	ThemeIcon,
	UnstyledButton,
	Badge,
	ActionIcon,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
	IconPhone,
	IconPlus,
	IconTrash,
	IconCheck,
	IconShield,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { radii, shadows } from "@app/styles/theme";
import { $phones, $isLoadingPhones } from "../model/stores";
import {
	fetchPhonesFx,
	requestPhoneOtpFx,
	verifyPhoneOtpFx,
	deletePhoneFx,
	type PhoneRow,
} from "../model/effects";

const MAX_ADDITIONAL_PHONES = 3;

export function PhoneManager() {
	const { t } = useTranslation("seller");
	const [phones, isLoading] = useUnit([$phones, $isLoadingPhones]);
	const [
		addModalOpened,
		{ open: openAddModal, close: closeAddModal },
	] = useDisclosure(false);
	const [
		deleteModalOpened,
		{ open: openDeleteModal, close: closeDeleteModal },
	] = useDisclosure(false);

	// Add-flow state
	const [phone, setPhone] = useState("");
	const [code, setCode] = useState("");
	const [otpRequested, setOtpRequested] = useState(false);
	const [otpRequestPending, setOtpRequestPending] = useState(false);
	const [verifyPending, setVerifyPending] = useState(false);

	// Delete-flow state
	const [pendingDelete, setPendingDelete] = useState<PhoneRow | null>(null);
	const [deleteAction, setDeleteAction] = useState<
		"transfer_to_primary" | "transfer_to_other" | "archive_listings"
	>("transfer_to_primary");
	const [deleteTargetPhone, setDeleteTargetPhone] = useState<string | null>(null);
	const [deletePending, setDeletePending] = useState(false);

	useEffect(() => {
		void fetchPhonesFx();
	}, []);

	const additionalCount = phones.filter((p) => !p.is_primary).length;
	const atMax = additionalCount >= MAX_ADDITIONAL_PHONES;

	const resetAddFlow = () => {
		setPhone("");
		setCode("");
		setOtpRequested(false);
		setOtpRequestPending(false);
		setVerifyPending(false);
	};

	const startAdd = () => {
		resetAddFlow();
		openAddModal();
	};

	const handleRequestOtp = async () => {
		if (!phone.trim()) return;
		setOtpRequestPending(true);
		try {
			await requestPhoneOtpFx({ phone: phone.trim() });
			setOtpRequested(true);
		} catch (err: any) {
			const detail = err?.response?.data?.detail;
			const code = typeof detail === "object" ? detail.code : null;
			let message: string = t("phones.toastErrorGeneric");
			if (code === "phone_in_use") message = t("phones.toastErrorPhoneInUse");
			else if (code === "phone_already_yours")
				message = "Этот номер уже привязан к вашему аккаунту";
			else if (code === "quota_exceeded")
				message = t("phones.toastErrorQuota");
			else if (typeof detail === "string") message = detail;
			notifications.show({ color: "red", message });
		} finally {
			setOtpRequestPending(false);
		}
	};

	const handleVerify = async () => {
		if (!phone.trim() || !code.trim()) return;
		setVerifyPending(true);
		try {
			const row = await verifyPhoneOtpFx({
				phone: phone.trim(),
				code: code.trim(),
			});
			closeAddModal();
			resetAddFlow();
			if (row.listings_count > 0) {
				notifications.show({
					color: "green",
					message: t("phones.toastAddedWithMatched", { count: row.listings_count }),
				});
			} else {
				notifications.show({ color: "green", message: t("phones.toastAdded") });
			}
		} catch (err: any) {
			const detail = err?.response?.data?.detail;
			let message: string = t("phones.toastErrorOtp");
			if (typeof detail === "string") message = detail;
			notifications.show({ color: "red", message });
		} finally {
			setVerifyPending(false);
		}
	};

	const startDelete = (p: PhoneRow) => {
		setPendingDelete(p);
		setDeleteAction("transfer_to_primary");
		setDeleteTargetPhone(null);
		openDeleteModal();
	};

	const confirmDelete = async () => {
		if (!pendingDelete) return;
		setDeletePending(true);
		try {
			await deletePhoneFx({
				phone_id: pendingDelete.id,
				action: deleteAction,
				target_phone_id:
					deleteAction === "transfer_to_other"
						? deleteTargetPhone || undefined
						: undefined,
			});
			closeDeleteModal();
			setPendingDelete(null);
			notifications.show({ color: "blue", message: t("phones.toastDeleted") });
		} catch (err: any) {
			const detail = err?.response?.data?.detail;
			notifications.show({
				color: "red",
				message:
					typeof detail === "string" ? detail : t("phones.toastErrorGeneric"),
			});
		} finally {
			setDeletePending(false);
		}
	};

	const otherPhonesForTransfer = phones.filter(
		(p) => pendingDelete && p.id !== pendingDelete.id,
	);

	return (
		<Box>
			<Text
				style={{ fontSize: 13, fontWeight: 500, color: "#8E8E93", marginBottom: 8 }}
			>
				{t("phones.pageTitle")}
			</Text>

			<Stack gap={8} mb={12}>
				{isLoading && phones.length === 0 ? (
					<>
						<Skeleton height={60} radius={radii.md} />
						<Skeleton height={60} radius={radii.md} />
					</>
				) : (
					phones.map((p) => (
						<Card
							key={p.id}
							padding="sm"
							style={{
								border: "1px solid #e2e8f0",
								borderRadius: radii.md,
								boxShadow: shadows.sm,
								background: "#fff",
							}}
						>
							<Group justify="space-between" wrap="nowrap" gap={12}>
								<Group gap={10} wrap="nowrap" style={{ flex: 1 }}>
									<ThemeIcon
										size={32}
										radius="xl"
										variant="light"
										color={p.is_primary ? "blue" : "gray"}
									>
										{p.is_primary ? <IconShield size={16} /> : <IconPhone size={16} />}
									</ThemeIcon>
									<Box>
										<Group gap={6}>
											<Text fw={700} c="dark.9" size="sm">{p.phone}</Text>
											{p.is_primary && (
												<Badge size="xs" color="blue" variant="filled">
													{t("phones.primaryBadge")}
												</Badge>
											)}
										</Group>
										{p.listings_count > 0 && (
											<Text size="xs" c="dimmed" mt={2}>
												{t("phones.listingsCount", { count: p.listings_count })}
											</Text>
										)}
									</Box>
								</Group>
								{!p.is_primary && (
									<ActionIcon
										variant="subtle"
										color="red"
										onClick={() => startDelete(p)}
										aria-label={t("phones.deleteModalTitle")}
									>
										<IconTrash size={18} />
									</ActionIcon>
								)}
							</Group>
						</Card>
					))
				)}
			</Stack>

			<Button
				leftSection={<IconPlus size={16} />}
				onClick={startAdd}
				disabled={atMax}
				variant="light"
				color="blue"
				size="sm"
				fullWidth
			>
				{atMax
					? t("phones.maxAdditionalReached", { max: MAX_ADDITIONAL_PHONES })
					: t("phones.addBtn")}
			</Button>

			{/* Add-phone modal */}
			<Modal
				opened={addModalOpened}
				onClose={() => { closeAddModal(); resetAddFlow(); }}
				title={t("phones.modalTitle")}
				centered
			>
				<Stack gap={12}>
					<TextInput
						label={t("phones.modalPhoneLabel")}
						placeholder={t("phones.modalPhonePlaceholder")}
						value={phone}
						onChange={(e) => setPhone(e.currentTarget.value)}
						disabled={otpRequested}
						required
					/>
					{otpRequested && (
						<TextInput
							label={t("phones.modalCodeLabel")}
							placeholder={t("phones.modalCodePlaceholder")}
							value={code}
							onChange={(e) => setCode(e.currentTarget.value)}
							description={t("phones.modalCodeHint")}
							required
							maxLength={6}
						/>
					)}
					<Group justify="flex-end" mt={4}>
						<Button variant="default" onClick={() => { closeAddModal(); resetAddFlow(); }}>
							{t("phones.modalCancelBtn")}
						</Button>
						{!otpRequested ? (
							<Button onClick={handleRequestOtp} loading={otpRequestPending}>
								{t("phones.modalSendOtpBtn")}
							</Button>
						) : (
							<Button onClick={handleVerify} loading={verifyPending}>
								{t("phones.modalVerifyBtn")}
							</Button>
						)}
					</Group>
				</Stack>
			</Modal>

			{/* Delete-phone modal */}
			<Modal
				opened={deleteModalOpened}
				onClose={closeDeleteModal}
				title={t("phones.deleteModalTitle")}
				centered
			>
				{pendingDelete && (
					<Stack gap={12}>
						<Text size="sm" c="dark.7">
							{pendingDelete.listings_count > 0
								? t("phones.deleteModalBody", { count: pendingDelete.listings_count })
								: t("phones.deleteModalEmptyBody")}
						</Text>

						{pendingDelete.listings_count > 0 && (
							<Stack gap={8}>
								<UnstyledButton
									onClick={() => setDeleteAction("transfer_to_primary")}
									style={{
										padding: 12,
										borderRadius: 8,
										background: deleteAction === "transfer_to_primary" ? "#dbeafe" : "#f8fafc",
										border: deleteAction === "transfer_to_primary"
											? "1px solid #3b82f6"
											: "1px solid #e2e8f0",
									}}
								>
									<Group gap={8}>
										{deleteAction === "transfer_to_primary" && <IconCheck size={16} color="#3b82f6" />}
										<Text size="sm" fw={500} c="dark.8">
											{t("phones.deleteAction.transferToPrimary")}
										</Text>
									</Group>
								</UnstyledButton>

								{otherPhonesForTransfer.filter((p) => !p.is_primary).length > 0 && (
									<UnstyledButton
										onClick={() => setDeleteAction("transfer_to_other")}
										style={{
											padding: 12,
											borderRadius: 8,
											background: deleteAction === "transfer_to_other" ? "#dbeafe" : "#f8fafc",
											border: deleteAction === "transfer_to_other"
												? "1px solid #3b82f6"
												: "1px solid #e2e8f0",
										}}
									>
										<Stack gap={6}>
											<Group gap={8}>
												{deleteAction === "transfer_to_other" && <IconCheck size={16} color="#3b82f6" />}
												<Text size="sm" fw={500} c="dark.8">
													{t("phones.deleteAction.transferToOther")}
												</Text>
											</Group>
											{deleteAction === "transfer_to_other" && (
												<Select
													size="xs"
													placeholder="Select..."
													value={deleteTargetPhone}
													onChange={setDeleteTargetPhone}
													data={otherPhonesForTransfer
														.filter((p) => !p.is_primary)
														.map((p) => ({ value: p.id, label: p.phone }))}
												/>
											)}
										</Stack>
									</UnstyledButton>
								)}

								<UnstyledButton
									onClick={() => setDeleteAction("archive_listings")}
									style={{
										padding: 12,
										borderRadius: 8,
										background: deleteAction === "archive_listings" ? "#fee2e2" : "#f8fafc",
										border: deleteAction === "archive_listings"
											? "1px solid #ef4444"
											: "1px solid #e2e8f0",
									}}
								>
									<Group gap={8}>
										{deleteAction === "archive_listings" && <IconCheck size={16} color="#ef4444" />}
										<Text size="sm" fw={500} c="dark.8">
											{t("phones.deleteAction.archiveListings")}
										</Text>
									</Group>
								</UnstyledButton>
							</Stack>
						)}

						<Group justify="flex-end" mt={4}>
							<Button variant="default" onClick={closeDeleteModal}>
								{t("phones.deleteAction.cancel")}
							</Button>
							<Button
								color="red"
								onClick={confirmDelete}
								loading={deletePending}
								disabled={deleteAction === "transfer_to_other" && !deleteTargetPhone}
							>
								{t("phones.deleteModalTitle")}
							</Button>
						</Group>
					</Stack>
				)}
			</Modal>
		</Box>
	);
}
