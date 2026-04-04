import { useEffect, useState } from "react";
import { useUnit } from "effector-react";
import { formatMonthYear } from "@shared/lib/date";
import {
	Container,
	Stack,
	Text,
	TextInput,
	Textarea,
	Button,
	Switch,
	Avatar,
	Badge,
	LoadingOverlay,
	Box,
	Group,
	SimpleGrid,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffectorNotification } from "@shared/hooks/useEffectorNotification";
import {
	IconUser,
	IconPhone,
	IconMail,
	IconBrandTelegram,
	IconBrandInstagram,
	IconWorld,
	IconCheck,
	IconEdit,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import {
	$sellerProfile,
	$isLoadingProfile,
	updateSellerProfile,
	updateSellerProfileFx,
} from "@modules/seller/shared/state";
import { StatCard } from "@shared/ui/StatCard";
import { FormSection } from "@shared/ui/FormSection";
import { IconList, IconEye } from "@tabler/icons-react";
import { ContactRow } from "../main/ContactRow";

function Page() {
	const { t } = useTranslation("seller");
	const [sellerProfile, isLoading] = useUnit([
		$sellerProfile,
		$isLoadingProfile,
	]);
	const [isEditing, setIsEditing] = useState(false);

	const form = useForm({
		initialValues: {
			company_name: "",
			description: "",
			email: "",
			phone_public: true,
			telegram_username: "",
			instagram_url: "",
			website_url: "",
		},
	});

	useEffect(() => {
		if (sellerProfile) {
			form.setValues({
				company_name: sellerProfile.company_name || "",
				description: sellerProfile.description || "",
				email: sellerProfile.email || "",
				phone_public: sellerProfile.phone_public,
				telegram_username: sellerProfile.telegram_username || "",
				instagram_url: sellerProfile.instagram_url || "",
				website_url: sellerProfile.website_url || "",
			});
		}
	}, [sellerProfile]);

	useEffectorNotification(
		updateSellerProfileFx,
		{
			title: t("notifications.success"),
			message: t("notifications.profileUpdated"),
			color: "green",
		},
		() => setIsEditing(false),
	);

	const handleSubmit = (values: typeof form.values) => {
		updateSellerProfile(values);
	};

	if (!sellerProfile) {
		return <LoadingOverlay visible />;
	}

	return (
		<Container size="sm" px="md" py="md">
			<LoadingOverlay visible={isLoading} />
			<Stack gap="md">
				{/* Profile Hero Card */}
				<Box
					style={{
						background:
							"linear-gradient(135deg, #228be6 0%, #40A7E3 50%, #74c0fc 100%)",
						borderRadius: 16,
						padding: "24px 20px",
						textAlign: "center",
						position: "relative",
						overflow: "hidden",
					}}
				>
					{/* Decorative */}
					<Box
						style={{
							position: "absolute",
							top: -15,
							right: -15,
							width: 80,
							height: 80,
							borderRadius: "50%",
							backgroundColor: "rgba(255,255,255,0.08)",
						}}
					/>

					<Avatar
						src={sellerProfile.logo_url}
						size={88}
						radius="xl"
						mx="auto"
						color="white"
						style={{
							border: "3px solid white",
							boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
						}}
					>
						<IconUser size={40} color="white" />
					</Avatar>

					<Group justify="center" gap="xs" mt="sm">
						<Text size="xl" fw={700} c="white">
							{sellerProfile.company_name || t("profile.seller")}
						</Text>
						{sellerProfile.is_verified && (
							<Badge
								color="white"
								variant="filled"
								size="sm"
								leftSection={<IconCheck size={10} />}
								style={{ backgroundColor: "rgba(64,192,87,0.9)" }}
							>
								{t("profile.verified")}
							</Badge>
						)}
					</Group>

					<Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
						{sellerProfile.phone}
					</Text>
					<Text size="xs" c="rgba(255,255,255,0.6)" mt={2}>
						{t("profile.memberSince", {
							date: formatMonthYear(sellerProfile.created_at),
						})}
					</Text>

					{!isEditing && (
						<Button
							variant="white"
							color="blue"
							size="xs"
							radius="xl"
							mt="sm"
							leftSection={<IconEdit size={14} />}
							onClick={() => setIsEditing(true)}
							style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}
						>
							{t("profile.edit")}
						</Button>
					)}
				</Box>

				{/* Stats Row */}
				<SimpleGrid cols={3} spacing="sm">
					<StatCard
						icon={IconList}
						color="blue"
						value={sellerProfile.listings_count}
						label={t("profile.listings")}
						compact
					/>
					<StatCard
						icon={IconEye}
						color="green"
						value={sellerProfile.total_views.toLocaleString("ru-RU")}
						label={t("profile.views")}
						compact
					/>
					<StatCard
						icon={IconPhone}
						color="orange"
						value={sellerProfile.total_contacts}
						label={t("profile.contacts")}
						compact
					/>
				</SimpleGrid>

				{/* Edit form or display */}
				{isEditing ? (
					<form onSubmit={form.onSubmit(handleSubmit)}>
						<Stack gap="sm">
							<FormSection title={t("profile.mainSection")}>
								<TextInput
									label={t("profile.companyName")}
									placeholder={t("profile.companyPlaceholder")}
									leftSection={<IconUser size={16} />}
									autoComplete="organization"
									{...form.getInputProps("company_name")}
								/>
								<Textarea
									label={t("profile.about")}
									placeholder={t("profile.aboutPlaceholder")}
									minRows={3}
									{...form.getInputProps("description")}
								/>
								<TextInput
									label={t("profile.email")}
									placeholder={t("profile.emailPlaceholder")}
									leftSection={<IconMail size={16} />}
									type="email"
									inputMode="email"
									autoComplete="email"
									{...form.getInputProps("email")}
								/>
								<Switch
									label={t("profile.showPhone")}
									{...form.getInputProps("phone_public", { type: "checkbox" })}
								/>
							</FormSection>

							<FormSection title={t("profile.socialMedia")}>
								<TextInput
									label={t("profile.telegram")}
									placeholder={t("profile.telegramPlaceholder")}
									leftSection={<IconBrandTelegram size={16} />}
									{...form.getInputProps("telegram_username")}
								/>
								<TextInput
									label={t("profile.instagram")}
									placeholder={t("profile.instagramPlaceholder")}
									leftSection={<IconBrandInstagram size={16} />}
									type="url"
									inputMode="url"
									{...form.getInputProps("instagram_url")}
								/>
								<TextInput
									label={t("profile.website")}
									placeholder={t("profile.websitePlaceholder")}
									leftSection={<IconWorld size={16} />}
									type="url"
									inputMode="url"
									{...form.getInputProps("website_url")}
								/>
							</FormSection>

							<Group justify="flex-end" mt="xs">
								<Button
									variant="light"
									color="gray"
									radius="md"
									onClick={() => setIsEditing(false)}
								>
									{t("profile.cancel")}
								</Button>
								<Button type="submit" loading={isLoading} radius="md">
									{t("profile.save")}
								</Button>
							</Group>
						</Stack>
					</form>
				) : (
					<Stack gap="sm">
						{/* About */}
						{sellerProfile.description && (
							<FormSection title={t("profile.about")}>
								<Text size="sm">{sellerProfile.description}</Text>
							</FormSection>
						)}

						{/* Contacts */}
						<FormSection title={t("profile.contactsSection")}>
							<ContactRow icon={IconPhone} label={sellerProfile.phone}>
								{!sellerProfile.phone_public && (
									<Badge size="xs" color="gray" variant="light">
										{t("profile.hidden")}
									</Badge>
								)}
							</ContactRow>
							{sellerProfile.email && (
								<ContactRow
									icon={IconMail}
									label={sellerProfile.email}
									href={`mailto:${sellerProfile.email}`}
								/>
							)}
						</FormSection>

						{/* Social */}
						{(sellerProfile.telegram_username ||
							sellerProfile.instagram_url ||
							sellerProfile.website_url) && (
							<FormSection title={t("profile.socialMedia")}>
								{sellerProfile.telegram_username && (
									<ContactRow
										icon={IconBrandTelegram}
										label={sellerProfile.telegram_username}
										href={`https://t.me/${sellerProfile.telegram_username.replace("@", "")}`}
									/>
								)}
								{sellerProfile.instagram_url && (
									<ContactRow
										icon={IconBrandInstagram}
										label={sellerProfile.instagram_url}
										href={sellerProfile.instagram_url}
									/>
								)}
								{sellerProfile.website_url && (
									<ContactRow
										icon={IconWorld}
										label={sellerProfile.website_url}
										href={sellerProfile.website_url}
									/>
								)}
							</FormSection>
						)}
					</Stack>
				)}
			</Stack>
		</Container>
	);
}

export const SellerProfileEdit = {
	route: "/seller/profile",
	Page,
};
