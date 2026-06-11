import { ReactNode } from "react";
import { Box } from "@mantine/core";
import { surface, spacing } from "@app/styles/theme";
import { TabBar } from "./TabBar";

interface RootPageProps {
	/** TabBar title; in fullscreen Telegram it renders inside the system
	 *  controls row even when tabBarChildren is provided (e.g. "UCHAR"
	 *  above the search bar on Home) */
	title?: string;
	/** Right-side actions in TabBar */
	actions?: ReactNode;
	/** Custom TabBar content (replaces the title row, e.g. search bar on Home) */
	tabBarChildren?: ReactNode;
	/** Page content */
	children: ReactNode;
	/** Disable default content padding (for pages that manage their own) */
	noPadding?: boolean;
}

/**
 * Page template for root tab screens (Home, Favorites, Settings).
 * Provides: surface background, TabBar, content area with safe-area padding.
 */
export function RootPage({
	title,
	actions,
	tabBarChildren,
	children,
	noPadding,
}: RootPageProps) {
	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			<TabBar title={title} actions={actions}>
				{tabBarChildren}
			</TabBar>
			{noPadding ? (
				children
			) : (
				<Box
					style={{
						padding: spacing.card,
						paddingBottom: "calc(80px + var(--safe-area-inset-bottom))",
					}}
				>
					{children}
				</Box>
			)}
		</Box>
	);
}
