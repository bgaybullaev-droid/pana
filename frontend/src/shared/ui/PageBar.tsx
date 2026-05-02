import { ReactNode } from "react";
import { Box, Text, ActionIcon } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useTelegram } from "@app/providers/useTelegram";
import { radii } from "@app/styles/theme";

interface PageBarProps {
	title: string;
	onBack?: () => void;
	actions?: ReactNode;
	badge?: ReactNode;
}

/**
 * Top app bar for inner pages (Notifications, Edit Profile, Seller pages, Admin pages).
 * Sticky, full-bleed background, back button on the left.
 */
export function PageBar({ title, onBack, actions, badge }: PageBarProps) {
	const navigate = useNavigate();
	const { webApp } = useTelegram();
	const handleBack = onBack || (() => navigate(-1));

	return (
		<Box
			style={{
				backgroundColor: "transparent",
				marginLeft: "calc(-50vw + 50%)",
				marginRight: "calc(-50vw + 50%)",
				width: "100vw",
			}}
		>
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
				{/* Back button */}
				{(!webApp?.initData && !navigator.userAgent.includes('Telegram')) ? (
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

				{/* Title + badge */}
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
		</Box>
	);
}
