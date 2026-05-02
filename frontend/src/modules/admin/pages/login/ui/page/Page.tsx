import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Container,
	Card,
	Stack,
	Title,
	Text,
	TextInput,
	PasswordInput,
	Button,
	ThemeIcon,
	Alert,
} from "@mantine/core";
import { IconShieldLock, IconAlertCircle } from "@tabler/icons-react";
import { useAuth } from "@app/providers/useAuth";
import {
	loginAsAdmin,
	$authError,
	$isAdminLoginLoading,
} from "@shared/state/auth/model";

function Page() {
	const navigate = useNavigate();
	const { t } = useTranslation("admin");
	const { user, isAuthenticated } = useAuth();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [authError, isLoading] = useUnit([$authError, $isAdminLoginLoading]);

	// Redirect to admin dashboard if already logged in as admin
	useEffect(() => {
		if (isAuthenticated && user?.role === "admin") {
			navigate("/admin");
		}
	}, [isAuthenticated, user, navigate]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (!username.trim() || !password.trim()) return;
		loginAsAdmin({ username: username.trim(), password: password.trim() });
	};

	return (
		<Container
			size="xs"
			px="md"
			py="xl"
			style={{ minHeight: "100vh", display: "flex", alignItems: "center" }}
		>
			<Card withBorder p="xl" w="100%" shadow="md">
				<form onSubmit={handleSubmit}>
					<Stack gap="lg" align="center">
						<ThemeIcon variant="light" color="blue" size={64} radius="xl">
							<IconShieldLock size={32} />
						</ThemeIcon>

						<Stack gap="xs" ta="center">
							<Title order={2}>{t("login.title")}</Title>
							<Text c="dimmed" size="sm">
								{t("login.subtitle")}
							</Text>
						</Stack>

						{authError && (
							<Alert
								icon={<IconAlertCircle size={16} />}
								color="red"
								variant="light"
								w="100%"
							>
								{authError}
							</Alert>
						)}

						<TextInput
							w="100%"
							label={t("login.username")}
							placeholder={t("login.usernamePlaceholder")}
							autoComplete="username"
							value={username}
							onChange={(e) => setUsername(e.currentTarget.value)}
							disabled={isLoading}
							required
						/>

						<PasswordInput
							w="100%"
							label={t("login.password")}
							placeholder={t("login.passwordPlaceholder")}
							autoComplete="current-password"
							value={password}
							onChange={(e) => setPassword(e.currentTarget.value)}
							disabled={isLoading}
							required
						/>

						<Button
							type="submit"
							loading={isLoading}
							disabled={!username.trim() || !password.trim()}
							w="100%"
							size="md"
						>
							{t("login.signIn")}
						</Button>

						<Button variant="subtle" size="sm" onClick={() => navigate("/")}>
							{t("login.backToHome")}
						</Button>
					</Stack>
				</form>
			</Card>
		</Container>
	);
}

export const AdminLogin = {
	route: "/admin/login",
	Page,
};
