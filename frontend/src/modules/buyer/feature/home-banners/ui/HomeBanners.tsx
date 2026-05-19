/**
 * Block phase-2 — buyer-side home banner injection.
 *
 * Tiny self-contained component that fetches active banners for a
 * placement + the user's current i18n language, then renders a single
 * Mantine <Paper> per banner (image + title overlay). Clicking records
 * the click and opens the target URL in a new tab.
 *
 * Designed to be plopped at the top of the buyer home feed without
 * coupling to home-page state.
 */

import { useEffect, useState } from "react";
import { Paper, Image, Box, Text, Stack } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { apiClient } from "@shared/api/client";

interface HomeBanner {
	id: string;
	title: string;
	image_url: string;
	target_url: string;
	placement: string;
	language: string;
}

interface HomeBannersProps {
	placement?: "home_top" | "home_inline" | "listing_inline";
}

function mapI18nToBannerLang(i18nLang: string): string {
	// i18next lang values: ru | uz | uz-cyrl | uz-latn  → backend: ru | uz | uz_cyrl
	if (i18nLang.startsWith("ru")) return "ru";
	if (i18nLang === "uz-cyrl") return "uz_cyrl";
	return "uz";
}

export function HomeBanners({ placement = "home_top" }: HomeBannersProps) {
	const { i18n } = useTranslation();
	const [banners, setBanners] = useState<HomeBanner[]>([]);

	useEffect(() => {
		let cancelled = false;
		const lang = mapI18nToBannerLang(i18n.language);
		apiClient
			.get<HomeBanner[]>("/banners/active", {
				params: { placement, lang },
			})
			.then((res) => {
				if (!cancelled) setBanners(res.data || []);
			})
			.catch(() => {
				// Silent — banners are optional decoration.
			});
		return () => {
			cancelled = true;
		};
	}, [placement, i18n.language]);

	if (banners.length === 0) return null;

	const handleClick = (banner: HomeBanner) => {
		// Fire-and-forget click counter, then open the URL.
		apiClient.post(`/banners/active/${banner.id}/click`).catch(() => {});
		window.open(banner.target_url, "_blank", "noopener,noreferrer");
	};

	return (
		<Stack gap="xs" mb="sm">
			{banners.map((b) => (
				<Paper
					key={b.id}
					radius="md"
					withBorder
					style={{
						overflow: "hidden",
						cursor: "pointer",
						position: "relative",
					}}
					onClick={() => handleClick(b)}
				>
					<Image
						src={b.image_url}
						alt={b.title}
						h={120}
						fit="cover"
						fallbackSrc="https://placehold.co/600x120?text=Banner"
					/>
					<Box
						style={{
							position: "absolute",
							bottom: 0,
							left: 0,
							right: 0,
							padding: "8px 12px",
							background:
								"linear-gradient(0deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 100%)",
						}}
					>
						<Text size="sm" fw={600} c="white">
							{b.title}
						</Text>
					</Box>
				</Paper>
			))}
		</Stack>
	);
}
