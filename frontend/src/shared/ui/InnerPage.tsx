import { ReactNode } from "react";
import { Box } from "@mantine/core";
import { surface, spacing } from "@app/styles/theme";
import { PageBar } from "./PageBar";

interface InnerPageProps {
	/** PageBar title */
	title: string;
	/** Custom back handler (defaults to navigate(-1)) */
	onBack?: () => void;
	/** Right-side actions in PageBar */
	actions?: ReactNode;
	/** Badge next to title */
	badge?: ReactNode;
	/** Page content */
	children: ReactNode;
	/** Disable default content padding (for pages that manage their own) */
	noPadding?: boolean;
	/** Optional custom background color */
	bg?: string;
}

/**
 * Page template for inner pages (all non-root screens).
 * Provides: surface background, PageBar with back button, content area with safe-area padding.
 */
export function InnerPage({
	title,
	onBack,
	actions,
	badge,
	children,
	noPadding,
	bg,
}: InnerPageProps) {
	return (
		<Box mih="100vh" style={{ backgroundColor: bg || surface.page }}>
			<PageBar title={title} onBack={onBack} actions={actions} badge={badge} />
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
