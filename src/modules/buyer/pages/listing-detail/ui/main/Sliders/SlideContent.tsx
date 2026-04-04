import { FC, useState, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
	Box,
	Text,
	ActionIcon,
	Stack,
	Avatar,
	Checkbox,
	Transition,
} from "@mantine/core";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination } from "swiper/modules";
import {
	IconHeart,
	IconMessageCircle,
	IconShare,
	IconInfoCircle,
} from "@tabler/icons-react";
import { IMAGE_BASE_URL, formatPrice } from "@app/styles/theme";
import type { BuyerListing } from "@shared/api/types";

import "swiper/css";
import "swiper/css/pagination";
import "./styles.css";

interface SlideContentProps {
	listing: BuyerListing;
	onLike: (id: string) => void;
	onMessage: (id: string) => void;
	onShare: (id: string) => void;
}

const defaultUserImage =
	'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"%3E%3Cpath fill="%23ccc" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/%3E%3C/svg%3E';

export const SlideContent: FC<SlideContentProps> = ({
	listing,
	onLike,
	onMessage,
	onShare,
}) => {
	const { t } = useTranslation("buyer");
	const [showInfo, setShowInfo] = useState(
		() => sessionStorage.getItem("slide_show_info") !== "false",
	);

	// Sync across all co-mounted slide instances via custom event
	useEffect(() => {
		const handler = (e: Event) => setShowInfo((e as CustomEvent).detail);
		window.addEventListener("slide-show-info", handler);
		return () => window.removeEventListener("slide-show-info", handler);
	}, []);

	const toggleShowInfo = useCallback(() => {
		setShowInfo((prev) => {
			const next = !prev;
			sessionStorage.setItem("slide_show_info", String(next));
			window.dispatchEvent(
				new CustomEvent("slide-show-info", { detail: next }),
			);
			return next;
		});
	}, []);
	const formattedPrice = formatPrice(listing.price);
	const sellerImageUrl = listing.sellerImage
		? `${IMAGE_BASE_URL}/${listing.sellerImage}`
		: defaultUserImage;

	return (
		<Box
			style={{
				height: "100vh",
				width: "100%",
				position: "relative",
				background: "hsl(300, 100%, 0%)",
			}}
		>
			{/* Seller Avatar */}
			<Box
				component="a"
				href={
					listing.sellerUserName
						? `https://t.me/${listing.sellerUserName}`
						: undefined
				}
				pos="absolute"
				top={7}
				right={12}
				style={{ zIndex: 99 }}
			>
				<Avatar
					src={sellerImageUrl}
					size={51}
					radius={30}
					styles={{
						root: {
							border: "1px solid #FFFFFF",
						},
						image: {
							objectFit: "cover",
							objectPosition: "top",
						},
					}}
				/>
			</Box>

			{/* Image Swiper */}
			<Swiper
				pagination={{ dynamicBullets: true }}
				modules={[Pagination]}
				className="listing-detail-swiper"
				style={{ height: "100%" }}
			>
				{listing.images.map((item, index) => (
					<SwiperSlide key={index}>
						<img
							src={`${IMAGE_BASE_URL}${item.imageUrl}`}
							alt=""
							style={{ width: "100%", height: "100%", objectFit: "cover" }}
						/>
					</SwiperSlide>
				))}
			</Swiper>

			{/* Gradient Overlay */}
			<Transition mounted={showInfo} transition="fade" duration={300}>
				{(styles) => (
					<Box
						pos="absolute"
						bottom={0}
						left={0}
						right={0}
						w="100%"
						h="40vh"
						style={{
							...styles,
							pointerEvents: "none",
							filter: "drop-shadow(0px 4px 4px rgba(0, 0, 0, 0.25))",
							background:
								"linear-gradient(180deg, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.8) 64.06%)",
							zIndex: 9,
						}}
					/>
				)}
			</Transition>

			{/* Action Buttons (Right Side Menu) */}
			<Box
				pos="absolute"
				bottom={6}
				right={0}
				pb={20}
				pr={10}
				style={{ zIndex: 9999 }}
			>
				<Stack gap={0} align="center">
					{/* Like Button */}
					<Stack gap={2} align="center" px={12}>
						<Checkbox
							icon={({ className }) => (
								<IconHeart
									className={className}
									size={29}
									fill={listing.isLiked ? "red" : "none"}
									color={listing.isLiked ? "red" : "white"}
								/>
							)}
							checked={listing.isLiked || false}
							onChange={() => onLike(listing.id)}
							styles={{
								root: { padding: 0 },
								input: { display: "none" },
								icon: { color: listing.isLiked ? "red" : "white" },
							}}
						/>
						<Text size="sm" fw={700} c="white" lh="15px">
							{listing.likes || 0}
						</Text>
					</Stack>

					{/* Message Button */}
					<Stack gap={2} align="center" px={12} mt={12}>
						<ActionIcon
							variant="transparent"
							size={29}
							onClick={() => onMessage(listing.id)}
						>
							<IconMessageCircle size={29} color="white" />
						</ActionIcon>
						<Text size="sm" fw={700} c="white" lh="15px">
							0
						</Text>
					</Stack>

					{/* Share Button */}
					<Stack gap={2} align="center" px={12} mt={12}>
						<ActionIcon
							variant="transparent"
							size={29}
							onClick={() => onShare(listing.id)}
						>
							<IconShare size={29} color="white" />
						</ActionIcon>
						<Text size="sm" fw={700} c="white" lh="15px">
							0
						</Text>
					</Stack>
				</Stack>
			</Box>

			{/* Product Info Section */}
			<Box pos="absolute" bottom={25} left={6} style={{ zIndex: 10 }}>
				{/* Info Toggle Button */}
				<ActionIcon
					variant="transparent"
					onClick={toggleShowInfo}
					pos={showInfo ? "relative" : "absolute"}
					bottom={showInfo ? 0 : 15}
				>
					<IconInfoCircle size={35} color="white" />
				</ActionIcon>

				{/* Product Info */}
				<Transition mounted={showInfo} transition="fade" duration={300}>
					{(styles) => (
						<Stack gap={3} style={styles} ml={8} maw={200}>
							<Text size="xs" fw={700} c="white" tt="capitalize">
								{listing.name}
							</Text>
							<Text size="sm" fw={600} c="white" lh="15px">
								{listing.description}
							</Text>
						</Stack>
					)}
				</Transition>

				{/* Price */}
				<Text size="sm" fw={600} c="white" lh="15px" ml={8} mt={5}>
					{formattedPrice} {t("common.currencySum")}
				</Text>
			</Box>
		</Box>
	);
};
