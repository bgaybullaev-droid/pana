import { Component, ErrorInfo, ReactNode } from "react";
import { Button, Container, Title, Text, Stack } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";

interface Props {
	children: ReactNode;
}

interface State {
	hasError: boolean;
	error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
	public state: State = {
		hasError: false,
		error: null,
	};

	public static getDerivedStateFromError(error: Error): State {
		return { hasError: true, error };
	}

	public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		console.error("Uncaught error:", error, errorInfo);

		// Specific handling for Vite's module loading errors or Outdated Optimize Dep
		if (
			error.message.includes("Failed to fetch dynamically imported module") ||
			error.message.includes("Importing a module script failed") ||
			error.message.includes("Outdated Optimize Dep") ||
			// Also checking stringified error just in case pattern matching differs across browsers
			String(error).includes("Failed to fetch") ||
			String(error).includes("dynamically imported module")
		) {
			const reloadCount = parseInt(sessionStorage.getItem("vite_reload") || "0", 10);
			if (reloadCount < 1) {
				sessionStorage.setItem("vite_reload", String(reloadCount + 1));
				window.location.reload();
			} else {
				sessionStorage.removeItem("vite_reload");
			}
		}
	}

	public render() {
		if (this.state.hasError) {
			return (
				<Container style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
					<Stack align="center" style={{ textAlign: "center" }}>
						<IconAlertTriangle size={64} color="red" />
						<Title order={2}>Что-то пошло не так</Title>
						<Text color="dimmed" size="sm" style={{ maxWidth: 400 }}>
							Произошла непредвиденная ошибка при загрузке страницы. Попробуйте обновить страницу.
						</Text>
						<Button variant="light" onClick={() => window.location.reload()}>
							Обновить страницу
						</Button>
					</Stack>
				</Container>
			);
		}

		return this.props.children;
	}
}
