import { ReactNode } from "react";
import { Box } from "@mantine/core";
import { surface, spacing } from "@app/styles/theme";
import { TabBar } from "./TabBar";

interface RootPageProps {
	/** TabBar title (ignored when tabBarChildren is provided) */
	title?: string;
	/** Right-side actions in TabBar */
	actions?: ReactNode;
	/** Custom TabBar content (replaces title, e.g. search bar on Home) */
	tabBarChildren?: ReactNode;
	/** Use translucent blur TabBar background */
	blur?: boolean;
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
	blur,
	children,
	noPadding,
}: RootPageProps) {
	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			<TabBar title={title} actions={actions} blur={blur}>
				{tabBarChildren}
			</TabBar>
			{noPadding ? (
				children
			) : (
				<Box
					style={{
						padding: spacing.card,
						paddingBottom: "calc(80px + env(safe-area-inset-bottom, 0px))",
					}}
				>
					{children}
				</Box>
			)}
		</Box>
	);
}
