import { ReactNode } from "react";
import { Box, Text } from "@mantine/core";
import { radii, shadows, surface } from "@app/styles/theme";

interface SectionCardProps {
	label?: string;
	children: ReactNode;
	marginTop?: number;
}

export function SectionCard({
	label,
	children,
	marginTop = 16,
}: SectionCardProps) {
	return (
		<Box style={{ marginTop }}>
			{label && (
				<Text
					size="xs"
					fw={600}
					c="dimmed"
					tt="uppercase"
					mb={8}
					style={{ letterSpacing: 0.5 }}
				>
					{label}
				</Text>
			)}
			<Box
				style={{
					backgroundColor: surface.card,
					borderRadius: radii.md,
					boxShadow: shadows.sm,
					overflow: "hidden",
				}}
			>
				{children}
			</Box>
		</Box>
	);
}
