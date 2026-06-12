import { ReactNode } from "react";
import { Box, Text } from "@mantine/core";
import { glass } from "@app/styles/theme";
import { useLayoutContext } from "@modules/buyer/app/ui/layout/BuyerLayout";
import { useTelegramTopInsets } from "@shared/hooks/useTelegramTopInsets";

interface TabBarProps {
	title?: string;
	actions?: ReactNode;
	children?: ReactNode;
}

/**
 * Top app bar for root tab screens (Home, Favorites, Settings).
 * Sticky, full-bleed frosted-glass background, no back button.
 * Pass `children` to render custom content (e.g. search bar + filter chips on Home).
 * In fullscreen Telegram the title renders inside the system controls row
 * (between Back and the minimize/close pill); elsewhere it falls back to a
 * regular 56px bar row.
 *
 * The title row never moves; only `children` (the search block on Home)
 * collapse on scroll, mirroring Telegram's own controls which stay put.
 */
export function TabBar({ title, actions, children }: TabBarProps) {
	const { headerVisible } = useLayoutContext();
	const { contentTop } = useTelegramTopInsets();
	const titleInSystemRow = contentTop > 0 && !!title;

	return (
		<Box
			component="header"
			style={{
				position: "sticky",
				top: 0,
				zIndex: 100,
				marginLeft: "calc(-50vw + 50%)",
				marginRight: "calc(-50vw + 50%)",
				width: "100vw",
				...glass,
				paddingTop: titleInSystemRow
					? "var(--safe-area-inset-top)"
					: "var(--app-top-inset)",
				borderBottom: "1px solid rgba(0,0,0,0.06)",
			}}
		>
			{/* Fullscreen: title lives in Telegram's controls row; side
			    paddings keep it clear of the Back chip and ⌄/… pill. */}
			{titleInSystemRow && (
				<Box
					style={{
						height: "var(--content-safe-area-inset-top)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						padding: "0 90px",
					}}
				>
					<Text
						truncate
						style={{
							fontSize: 17,
							fontWeight: 700,
							color: "#1C1C1E",
							maxWidth: "100%",
						}}
					>
						{title}
					</Text>
				</Box>
			)}
			{children ? (
				/* Collapsible zone — the only part that hides on scroll.
				   Animated via grid-template-rows (0fr clips the content);
				   on engines without fr-animation it just snaps. */
				<Box
					style={{
						display: "grid",
						gridTemplateRows: headerVisible ? "1fr" : "0fr",
						transition:
							"grid-template-rows 0.4s cubic-bezier(0.4, 0.6, 0.2, 1)",
						pointerEvents: headerVisible ? "auto" : "none",
					}}
				>
					<Box style={{ overflow: "hidden", minHeight: 0 }}>{children}</Box>
				</Box>
			) : !titleInSystemRow || actions ? (
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
					{!titleInSystemRow && (
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
					)}
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
			) : null}
		</Box>
	);
}
