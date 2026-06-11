import { FC } from "react";
import { Box, Portal, UnstyledButton } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { shadows } from "@app/styles/theme";

interface DrawerBackButtonProps {
	/** Render the button only while the drawer is open. */
	opened: boolean;
	onClose: () => void;
	/**
	 * Same portal target as the parent drawer: the seller Stage-2 preview frame
	 * (which establishes a containing block via `transform`), or `null`/
	 * `undefined` for the full viewport.
	 */
	container?: HTMLElement | null;
}

/**
 * Dark round "back" button shared by the listing drawers.
 *
 * It lives in its own portal — a sibling of the Drawer rather than a child of
 * its sliding content — so it stays pinned to the bottom-right: it appears in
 * place when the drawer opens (no slide-up) and never shifts while the sheet is
 * dragged. The geometry mirrors the listing page's own back button (see
 * listing-detail `Page.tsx`) so the two line up pixel-for-pixel, and it sits
 * above the drawer (zIndex 10002 > drawer 10001).
 */
export const DrawerBackButton: FC<DrawerBackButtonProps> = ({
	opened,
	onClose,
	container,
}) => {
	const { t } = useTranslation("buyer");
	if (!opened) return null;

	return (
		<Portal target={container ?? undefined}>
			<Box
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					paddingBottom: "var(--safe-area-inset-bottom)",
					zIndex: 10002,
					pointerEvents: "none",
				}}
			>
				<Box
					style={{
						maxWidth: 500,
						margin: "0 auto",
						position: "relative",
						height: 72,
					}}
				>
					<UnstyledButton
						onClick={onClose}
						aria-label={t("descriptionDrawer.back", "Назад")}
						style={{
							position: "absolute",
							bottom: 12,
							right: 12,
							width: 45,
							height: 45,
							borderRadius: "50%",
							backgroundColor: "rgba(0, 0, 0, 0.6)",
							backdropFilter: "blur(20px) saturate(180%)",
							WebkitBackdropFilter: "blur(20px) saturate(180%)",
							border: "1px solid rgba(255, 255, 255, 0.25)",
							boxShadow: shadows.md,
							pointerEvents: "auto",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<IconArrowLeft size={24} stroke={1.8} color="#fff" />
					</UnstyledButton>
				</Box>
			</Box>
		</Portal>
	);
};
