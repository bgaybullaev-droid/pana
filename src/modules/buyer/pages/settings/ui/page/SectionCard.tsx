import { ReactNode } from "react";
import { Box, Text } from "@mantine/core";

interface SectionCardProps {
	label?: string;
	children: ReactNode;
	marginTop?: number;
}

export function SectionCard({
	label,
	children,
	marginTop = 20,
}: SectionCardProps) {
	return (
		<Box style={{ marginTop }}>
			{label && (
				<Text
					style={{
						fontSize: 12,
						fontWeight: 600,
						color: "#8E8E93",
						textTransform: "uppercase",
						letterSpacing: 0.8,
						marginLeft: 32,
						marginBottom: 6,
					}}
				>
					{label}
				</Text>
			)}
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					marginLeft: 16,
					marginRight: 16,
					overflow: "hidden",
				}}
			>
				{children}
			</Box>
		</Box>
	);
}
