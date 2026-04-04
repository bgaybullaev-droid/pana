import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Text, ActionIcon } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";

interface SubPageLayoutProps {
	title: string;
	children: ReactNode;
}

export function SubPageLayout({ title, children }: SubPageLayoutProps) {
	const navigate = useNavigate();

	return (
		<Box mih="100vh" style={{ backgroundColor: "#F5F5F7", overflow: "auto" }}>
			{/* Sticky top bar */}
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
					{title}
				</Text>
			</Box>

			{/* Content area */}
			<Box
				style={{
					padding: 16,
					paddingBottom: "calc(80px + env(safe-area-inset-bottom, 0px))",
				}}
			>
				{children}
			</Box>
		</Box>
	);
}
