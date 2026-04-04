import { useState } from "react";
import { UnstyledButton, Text, Box } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";

interface CTAButtonProps {
	label: string;
	onClick: () => void;
}

export function CTAButton({ label, onClick }: CTAButtonProps) {
	const [pressed, setPressed] = useState(false);

	return (
		<Box style={{ padding: "12px 16px 0" }}>
			<UnstyledButton
				onClick={onClick}
				onMouseDown={() => setPressed(true)}
				onMouseUp={() => setPressed(false)}
				onMouseLeave={() => setPressed(false)}
				onTouchStart={() => setPressed(true)}
				onTouchEnd={() => setPressed(false)}
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					gap: 8,
					width: "100%",
					height: 50,
					borderRadius: 14,
					backgroundColor: pressed ? "#1557B0" : "#1A73E8",
					transform: pressed ? "scale(0.98)" : "scale(1)",
					transition: "all 120ms ease-out",
				}}
			>
				<IconPlus size={18} color="#FFFFFF" stroke={2.5} />
				<Text
					style={{
						fontSize: 16,
						fontWeight: 600,
						color: "#FFFFFF",
					}}
				>
					{label}
				</Text>
			</UnstyledButton>
		</Box>
	);
}
