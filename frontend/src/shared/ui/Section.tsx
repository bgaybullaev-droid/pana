import { ReactNode } from "react";
import { Box, Stack } from "@mantine/core";
import { radii, shadows, spacing, surface } from "@app/styles/theme";

interface SectionProps {
	/** Section variant */
	variant?: "default" | "card" | "list";
	/** Section content */
	children: ReactNode;
	/** Gap between children (default: "md") */
	gap?: number | string;
}

/**
 * Content section within a page.
 *
 * - default: vertical stack with standard gap, no background
 * - card: white card with shadow, padding, rounded corners
 * - list: white card without internal padding (for list items that handle their own)
 */
export function Section({ variant = "default", children, gap = "md" }: SectionProps) {
	if (variant === "card") {
		return (
			<Box
				style={{
					backgroundColor: surface.card,
					borderRadius: radii.md,
					padding: spacing.card,
					boxShadow: shadows.sm,
				}}
			>
				<Stack gap={gap}>{children}</Stack>
			</Box>
		);
	}

	if (variant === "list") {
		return (
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
		);
	}

	// default
	return <Stack gap={gap}>{children}</Stack>;
}
