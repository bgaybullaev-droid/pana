import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import { updateProfileFx } from "@shared/state/auth/model/effects";
import { radii } from "@app/styles/theme";
import {
	Box,
	Text,
	TextInput,
	Button,
	Avatar,
} from "@mantine/core";
import { IconUser } from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import { ChipSelect } from "@shared/ui/ChipSelect";
import { PhoneManager } from "@modules/seller/feature/phone-manager";

function Page() {
	const { t } = useTranslation("buyer");
	const { user } = useAuth();
	const navigate = useNavigate();

	const [firstName, setFirstName] = useState(user?.first_name || "");
	const [lastName, setLastName] = useState(user?.last_name || "");
	const [sellerType, setSellerType] = useState(user?.seller_type || "");
	const [sellerTelegram, setSellerTelegram] = useState(user?.seller_telegram || "");
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const initials =
		(user?.first_name?.[0] || "") + (user?.last_name?.[0] || "") ||
		user?.username?.[0]?.toUpperCase() ||
		"U";

	const hasChanges =
		firstName !== (user?.first_name || "") ||
		lastName !== (user?.last_name || "") ||
		sellerType !== (user?.seller_type || "") ||
		sellerTelegram !== (user?.seller_telegram || "");

	const handleSave = async () => {
		if (!firstName.trim()) {
			setError(t("editProfile.firstNameRequired"));
			return;
		}

		setSaving(true);
		setError(null);

		try {
			const data: {
				first_name?: string;
				last_name?: string;
				seller_type?: string;
				seller_telegram?: string;
			} = {};

			if (firstName !== user?.first_name) data.first_name = firstName.trim();
			if (lastName !== (user?.last_name || ""))
				data.last_name = lastName.trim() || undefined;
			if (sellerType !== (user?.seller_type || ""))
				data.seller_type = sellerType || undefined;
			if (sellerTelegram !== (user?.seller_telegram || ""))
				data.seller_telegram = sellerTelegram.trim() || undefined;

			await updateProfileFx(data);
			navigate(-1);
		} catch {
			setError(t("editProfile.saveError"));
		} finally {
			setSaving(false);
		}
	};

	return (
		<InnerPage title={t("editProfile.title")}>
				{/* Avatar section */}
				<Box
					style={{
						display: "flex",
						justifyContent: "center",
						marginBottom: 24,
						marginTop: 8,
					}}
				>
					<Avatar
						src={user?.avatar_url}
						size={80}
						radius={radii.full}
						styles={{
							placeholder: {
								backgroundColor: "#E8F0FE",
								color: "#1A73E8",
								fontSize: 24,
								fontWeight: 600,
							},
						}}
					>
						{user?.avatar_url ? undefined : initials || <IconUser size={32} />}
					</Avatar>
				</Box>

				{/* Form */}
				<Box
					style={{
						backgroundColor: "#FFFFFF",
						borderRadius: radii.md,
						padding: 20,
						marginBottom: 16,
					}}
				>
					<TextInput
						label={t("editProfile.firstName")}
						value={firstName}
						onChange={(e) => setFirstName(e.currentTarget.value)}
						placeholder={t("editProfile.firstNamePlaceholder")}
						autoComplete="given-name"
						required
						mb={16}
						styles={{
							label: {
								fontSize: 13,
								fontWeight: 500,
								color: "#8E8E93",
								marginBottom: 6,
							},
							input: {
								height: 48,
								borderRadius: radii.md,
								borderColor: "#E8E8ED",
								fontSize: 16,
								"&:focus": {
									borderColor: "#1A73E8",
								},
							},
						}}
					/>

					<TextInput
						label={t("editProfile.lastName")}
						value={lastName}
						onChange={(e) => setLastName(e.currentTarget.value)}
						placeholder={t("editProfile.lastNamePlaceholder")}
						autoComplete="family-name"
						mb={16}
						styles={{
							label: {
								fontSize: 13,
								fontWeight: 500,
								color: "#8E8E93",
								marginBottom: 6,
							},
							input: {
								height: 48,
								borderRadius: radii.md,
								borderColor: "#E8E8ED",
								fontSize: 16,
								"&:focus": {
									borderColor: "#1A73E8",
								},
							},
						}}
					/>

					<Box mb={16}>
						<PhoneManager />
					</Box>

					<Box mb={16}>
						<ChipSelect
							label={t("editProfile.sellerTypeLabel")}
							showOptionalHint={false}
							options={[
								{ value: "owner", label: t("editProfile.sellerTypeOwner") },
								{ value: "realtor", label: t("editProfile.sellerTypeRealtor") },
								{ value: "developer", label: t("editProfile.sellerTypeDeveloper") },
							]}
							value={sellerType}
							onChange={(val) => setSellerType((val as string) || "")}
						/>
					</Box>

					<TextInput
						label={t("editProfile.telegramLabel")}
						placeholder={t("editProfile.telegramPlaceholder")}
						description={t("editProfile.telegramDescription")}
						value={sellerTelegram}
						onChange={(e) => setSellerTelegram(e.currentTarget.value)}
						styles={{
							label: {
								fontSize: 13,
								fontWeight: 500,
								color: "#8E8E93",
								marginBottom: 6,
							},
							input: {
								height: 48,
								borderRadius: radii.md,
								borderColor: "#E8E8ED",
								fontSize: 16,
								"&:focus": {
									borderColor: "#1A73E8",
								},
							},
						}}
					/>
				</Box>

				{error && (
					<Text
						style={{
							fontSize: 14,
							color: "#FF3B30",
							textAlign: "center",
							marginBottom: 16,
						}}
					>
						{error}
					</Text>
				)}

				{/* Save button */}
				<Button
					fullWidth
					radius={radii.md}
					size="lg"
					onClick={handleSave}
					loading={saving}
					disabled={!hasChanges || !firstName.trim()}
					styles={{
						root: {
							height: 50,
							fontSize: 16,
							fontWeight: 600,
							backgroundColor: "#1A73E8",
							"&:disabled": {
								backgroundColor: "#E8E8ED",
								color: "#8E8E93",
							},
						},
					}}
				>
					{t("editProfile.save")}
				</Button>
		</InnerPage>
	);
}

export const EditProfile = {
	route: "/edit-profile",
	Page,
};
