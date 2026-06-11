import { ReactNode } from "react";
import { Box, Text, ActionIcon } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useTelegram } from "@app/providers/useTelegram";
import { glass, radii } from "@app/styles/theme";
import { useTelegramTopInsets } from "@shared/hooks/useTelegramTopInsets";

interface PageBarProps {
	title: string;
	onBack?: () => void;
	actions?: ReactNode;
	badge?: ReactNode;
	/** Custom content for the left slot (e.g. a menu Burger). Overrides the back button when set. */
	leftSlot?: ReactNode;
}

/**
 * Top app bar for inner pages (Notifications, Edit Profile, Seller pages, Admin pages).
 * Sticky frosted-glass bar, back button on the left (browser only — Telegram
 * shows its native Back). In fullscreen Telegram the title renders inside the
 * system controls row, between Back and the minimize/close pill.
 */
export function PageBar({ title, onBack, actions, badge, leftSlot }: PageBarProps) {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const { contentTop } = useTelegramTopInsets();
	const handleBack = onBack || (() => navigate(-1));
	const titleInSystemRow = contentTop > 0;
	// The 56px row only remains useful for its slots once the title moved up.
	const showClassicRow = !titleInSystemRow || !!leftSlot || !!actions;

	return (
		<Box
			style={{
				position: "sticky",
				top: 0,
				zIndex: 100,
				...glass,
				borderBottom: "1px solid rgba(0,0,0,0.06)",
				marginLeft: "calc(-50vw + 50%)",
				marginRight: "calc(-50vw + 50%)",
				width: "100vw",
				paddingTop: titleInSystemRow
					? "var(--safe-area-inset-top)"
					: "var(--app-top-inset)",
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
						gap: 8,
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
					{badge}
				</Box>
			)}
			{showClassicRow && (
				<Box
					style={{
						maxWidth: 980,
						margin: "0 auto",
						height: 56,
						display: "flex",
						alignItems: "center",
						padding: "0 16px",
						position: "relative",
					}}
				>
					{/* Left slot: custom content (e.g. menu Burger) overrides the back button */}
					{leftSlot ? (
						<Box style={{ flexShrink: 0, display: "flex", alignItems: "center" }}>
							{leftSlot}
						</Box>
					) : (!webApp?.initData && !navigator.userAgent.includes('Telegram')) ? (
						<ActionIcon
							variant="default"
							size={40}
							radius={radii.full}
							onClick={handleBack}
							style={{
								flexShrink: 0,
								backgroundColor: "#ffffff",
								border: "1px solid #e9ecef",
								boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
							}}
						>
							<IconArrowLeft size={20} stroke={1.8} color="#495057" />
						</ActionIcon>
					) : (
						<Box style={{ width: 40, flexShrink: 0 }} />
					)}

					{/* Title + badge (moved to the system row in fullscreen) */}
					<Box
						style={{
							flex: 1,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: 8,
							marginRight: actions ? 0 : 40,
						}}
					>
						{!titleInSystemRow && (
							<>
								<Text
									style={{
										fontSize: 17,
										fontWeight: 600,
										color: "#1C1C1E",
									}}
									truncate
								>
									{title}
								</Text>
								{badge}
							</>
						)}
					</Box>

					{/* Right actions */}
					{actions && (
						<Box
							style={{
								display: "flex",
								alignItems: "center",
								flexShrink: 0,
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
