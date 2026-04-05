import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Text, UnstyledButton, Collapse } from "@mantine/core";
import { IconChevronDown } from "@tabler/icons-react";
import { PageBar } from "@shared/ui/PageBar";
import { surface } from "@app/styles/theme";

const FAQ_COUNT = 6;

function Page() {
	const { t } = useTranslation("buyer");
	const [openIndex, setOpenIndex] = useState<number | null>(null);

	const toggle = (i: number) => {
		setOpenIndex(openIndex === i ? null : i);
	};

	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			<PageBar title={t("settings.faq")} />
			<Box style={{ padding: 16, paddingBottom: "calc(80px + env(safe-area-inset-bottom, 0px))" }}>
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					overflow: "hidden",
				}}
			>
				{Array.from({ length: FAQ_COUNT }, (_, i) => {
					const isOpen = openIndex === i;
					const isLast = i === FAQ_COUNT - 1;

					return (
						<Box key={i}>
							<UnstyledButton
								onClick={() => toggle(i)}
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: "space-between",
									width: "100%",
									padding: "16px",
									gap: 12,
								}}
							>
								<Text
									style={{
										fontSize: 15,
										fontWeight: 500,
										color: "#1C1C1E",
										flex: 1,
										lineHeight: 1.4,
									}}
								>
									{t(`faq.q${i + 1}`)}
								</Text>
								<IconChevronDown
									size={18}
									color="#8E8E93"
									style={{
										flexShrink: 0,
										transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
										transition: "transform 200ms ease",
									}}
								/>
							</UnstyledButton>

							<Collapse in={isOpen}>
								<Box style={{ padding: "0 16px 16px" }}>
									<Text
										style={{
											fontSize: 14,
											color: "#8E8E93",
											lineHeight: 1.6,
										}}
									>
										{t(`faq.a${i + 1}`)}
									</Text>
								</Box>
							</Collapse>

							{!isLast && (
								<Box
									style={{
										height: 0.5,
										backgroundColor: "#E8E8ED",
										marginLeft: 16,
									}}
								/>
							)}
						</Box>
					);
				})}
			</Box>
			</Box>
		</Box>
	);
}

export const FAQ = {
	route: "/faq",
	Page,
};
