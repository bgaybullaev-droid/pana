import { ReactNode } from "react";
import { Box, Text } from "@mantine/core";
import { surface } from "@app/styles/theme";

interface TabBarProps {
	title?: string;
	actions?: ReactNode;
	children?: ReactNode;
	/** Use translucent blur background instead of solid white */
	blur?: boolean;
}

/**
 * Top app bar for root tab screens (Home, Favorites, Settings).
 * Sticky, full-bleed background, no back button.
 * Pass `children` to render custom content (e.g. search bar + filter chips on Home).
 * When `children` is provided, height is auto and inner content is unconstrained.
 */
export function TabBar({ title, actions, children, blur }: TabBarProps) {
	const bg = blur
		? {
				backgroundColor: "rgba(255,255,255,0.92)",
				backdropFilter: "blur(20px)",
				WebkitBackdropFilter: "blur(20px)",
			}
		: { backgroundColor: surface.card };

	return (
		<Box
			style={{
				position: "sticky",
				top: 0,
				zIndex: 100,
				...bg,
				borderBottom: "1px solid rgba(0,0,0,0.06)",
				marginLeft: "calc(-50vw + 50%)",
				marginRight: "calc(-50vw + 50%)",
				width: "100vw",
			}}
		>
			{children || (
				<Box
					style={{
						maxWidth: 980,
						margin: "0 auto",
						height: 56,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						padding: "0 16px",
						position: "relative",
					}}
				>
					<Text
						style={{
							fontSize: 17,
							fontWeight: 600,
							color: "#1C1C1E",
							textAlign: "center",
							flex: 1,
						}}
					>
						{title}
					</Text>
					{actions && (
						<Box
							style={{
								position: "absolute",
								right: 16,
								top: 0,
								bottom: 0,
								display: "flex",
								alignItems: "center",
							}}
						>
							{actions}
						</Box>
					)}
				</Box>
			)}
		</Box>
	);
}
