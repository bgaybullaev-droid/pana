import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import { updateProfileFx } from "@shared/state/auth/model/effects";
import {
	Box,
	Text,
	TextInput,
	Button,
	Avatar,
	ActionIcon,
} from "@mantine/core";
import { IconArrowLeft, IconUser } from "@tabler/icons-react";

function Page() {
	const { t } = useTranslation("buyer");
	const { user } = useAuth();
	const navigate = useNavigate();

	const [firstName, setFirstName] = useState(user?.first_name || "");
	const [lastName, setLastName] = useState(user?.last_name || "");
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const initials =
		(user?.first_name?.[0] || "") + (user?.last_name?.[0] || "") ||
		user?.username?.[0]?.toUpperCase() ||
		"U";

	const hasChanges =
		firstName !== (user?.first_name || "") ||
		lastName !== (user?.last_name || "");

	const handleSave = async () => {
		if (!firstName.trim()) {
			setError(t("editProfile.firstNameRequired"));
			return;
		}

		setSaving(true);
		setError(null);

		try {
			const data: { first_name?: string; last_name?: string } = {};

			if (firstName !== user?.first_name) data.first_name = firstName.trim();
			if (lastName !== (user?.last_name || ""))
				data.last_name = lastName.trim() || undefined;

			await updateProfileFx(data);
			navigate(-1);
		} catch {
			setError(t("editProfile.saveError"));
		} finally {
			setSaving(false);
		}
	};

	return (
		<Box mih="100vh" style={{ backgroundColor: "#F5F5F7" }}>
			{/* Top bar */}
			<Box
				style={{
					position: "sticky",
					top: 0,
					zIndex: 100,
					height: 56,
					backgroundColor: "#FFFFFF",
					borderBottom: "1px solid #E8E8ED",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
				}}
			>
				<ActionIcon
					variant="transparent"
					onClick={() => navigate(-1)}
					style={{ position: "absolute", left: 12 }}
					size={36}
				>
					<IconArrowLeft size={24} color="#1C1C1E" />
				</ActionIcon>
				<Text
					style={{
						fontSize: 17,
						fontWeight: 600,
						color: "#1C1C1E",
					}}
				>
					{t("editProfile.title")}
				</Text>
			</Box>

			<Box style={{ padding: 16 }}>
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
						radius="50%"
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
						borderRadius: 14,
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
								borderRadius: 12,
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
								borderRadius: 12,
								borderColor: "#E8E8ED",
								fontSize: 16,
								"&:focus": {
									borderColor: "#1A73E8",
								},
							},
						}}
					/>

					{user?.phone && (
						<Box>
							<Text
								style={{
									fontSize: 13,
									fontWeight: 500,
									color: "#8E8E93",
									marginBottom: 6,
								}}
							>
								{t("editProfile.phone")}
							</Text>
							<Box
								style={{
									height: 48,
									borderRadius: 12,
									border: "1px solid #E8E8ED",
									backgroundColor: "#F5F5F7",
									display: "flex",
									alignItems: "center",
									paddingLeft: 12,
									paddingRight: 12,
								}}
							>
								<Text
									style={{
										fontSize: 16,
										color: "#8E8E93",
									}}
								>
									{user.phone}
								</Text>
							</Box>
						</Box>
					)}
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
					radius={14}
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
			</Box>
		</Box>
	);
}

export const EditProfile = {
	route: "/edit-profile",
	Page,
};
