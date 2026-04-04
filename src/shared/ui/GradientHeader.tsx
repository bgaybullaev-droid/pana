import { FC, ReactNode } from "react";
import { ActionIcon, Box, Text } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { gradients } from "@app/styles/theme";
import type { TablerIconsProps } from "@tabler/icons-react";

type GradientType = "header" | "primary" | "orange";

interface GradientHeaderProps {
	icon: FC<TablerIconsProps>;
	title: string;
	subtitle?: string;
	gradient?: GradientType;
	onBack?: () => void;
	children?: ReactNode;
}

const gradientMap: Record<GradientType, string> = {
	header: gradients.header,
	primary: gradients.primary,
	orange: gradients.orange,
};

export function GradientHeader({
	icon: Icon,
	title,
	subtitle,
	gradient = "header",
	onBack,
	children,
}: GradientHeaderProps) {
	return (
		<Box
			style={{
				background: gradientMap[gradient],
				padding: "48px 20px 60px",
				textAlign: "center",
				position: "relative",
				overflow: "hidden",
			}}
		>
			{/* Decorative circles */}
			<Box
				style={{
					position: "absolute",
					top: -30,
					right: -30,
					width: 120,
					height: 120,
					borderRadius: "50%",
					backgroundColor: "rgba(255,255,255,0.08)",
				}}
			/>
			<Box
				style={{
					position: "absolute",
					bottom: 10,
					left: -20,
					width: 80,
					height: 80,
					borderRadius: "50%",
					backgroundColor: "rgba(255,255,255,0.06)",
				}}
			/>

			{onBack && (
				<ActionIcon
					variant="transparent"
					size={56}
					onClick={onBack}
					style={{
						position: "absolute",
						top: 12,
						left: 12,
						zIndex: 2,
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: "0 4px 20px rgba(0, 0, 0, 0.04)",
						borderRadius: "50%",
					}}
				>
					<IconArrowLeft size={24} color="#868e96" />
				</ActionIcon>
			)}

			{children}

			<Box
				style={{
					width: 72,
					height: 72,
					borderRadius: "50%",
					backgroundColor: "rgba(255,255,255,0.15)",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					margin: "0 auto 16px",
				}}
			>
				<Icon size={36} color="white" stroke={1.5} />
			</Box>
			<Text size="xl" fw={700} c="white">
				{title}
			</Text>
			{subtitle && (
				<Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
					{subtitle}
				</Text>
			)}
		</Box>
	);
}
