import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
	Box,
	Text,
	Avatar,
	Stack,
	Group,
	ActionIcon,
	LoadingOverlay,
	Container,
	Paper,
	Button,
	Card,
	Badge,
	ThemeIcon,
} from "@mantine/core";
import {
	IconArrowLeft,
	IconPhone,
	IconBrandTelegram,
	IconBrandInstagram,
	IconWorld,
	IconShieldCheck,
	IconInfoCircle,
	IconShare,
	IconHome2,
	IconChevronRight,
	IconBuilding,
	IconEye,
	IconCalendarEvent,
	IconList,
} from "@tabler/icons-react";
import { apiClient } from "@shared/api/client";
import { shadows, radii, surface } from "@app/styles/theme";
import type { SellerPublic, ListingListItem } from "@shared/api/types";
import { ListingCard } from "@shared/ui/ListingCard";

interface SellerListingsResponse {
	items: ListingListItem[];
	total: number;
	page: number;
	per_page: number;
}

function Page() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const [seller, setSeller] = useState<SellerPublic | null>(null);
	const [listings, setListings] = useState<ListingListItem[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		if (!id) return;
		const load = async () => {
			try {
				const [sellerRes, listingsRes] = await Promise.all([
					apiClient.get<SellerPublic>(`/sellers/${id}`),
					apiClient.get<SellerListingsResponse>(
						`/sellers/${id}/listings?per_page=50`,
					),
				]);
				setSeller(sellerRes.data);
				setListings(listingsRes.data.items || []);
			} catch (err) {
				console.error("Error loading seller profile:", err);
			} finally {
				setLoading(false);
			}
		};
		load();
	}, [id]);

	const handleShare = () => {
		if (navigator.share) {
			navigator
				.share({
					title: seller?.company_name || "Seller Profile",
					url: window.location.href,
				})
				.catch(() => {});
		} else {
			navigator.clipboard.writeText(window.location.href);
		}
	};

	if (loading) return <LoadingOverlay visible />;

	if (!seller) {
		return (
			<Box p="xl" ta="center" pt={100}>
				<IconInfoCircle size={48} color="var(--mantine-color-gray-4)" />
				<Text c="dimmed" mt="md" fw={500}>
					Seller not found
				</Text>
				<Button variant="subtle" mt="lg" onClick={() => navigate("/")}>
					Go to Home
				</Button>
			</Box>
		);
	}

	const memberYear = new Date(seller.created_at).getFullYear();
	const yearsActive = new Date().getFullYear() - memberYear || 1;
	const totalViews = listings.reduce((s, l) => s + (l.views_count || 0), 0);

	return (
		<Container
			px={0}
			style={{
				backgroundColor: surface.page,
				minHeight: "100vh",
				maxWidth: 980,
				margin: "0 auto",
				overflow: "auto",
			}}
		>
			{/* ── Compact Cover Area — gradient extends under the fullscreen
			    system zone, controls sit below it ── */}
			<Box
				style={{
					height: "calc(120px + var(--app-top-inset))",
					background: "linear-gradient(135deg, #228be6, #1864ab)",
					position: "relative",
					borderBottomLeftRadius: 24,
					borderBottomRightRadius: 24,
					boxShadow: "inset 0 -10px 20px rgba(0,0,0,0.05)",
				}}
			>
				<ActionIcon
					variant="transparent"
					size={56}
					onClick={() => navigate(-1)}
					style={{
						position: "absolute",
						top: "calc(var(--app-top-inset) + 12px)",
						left: 12,
						zIndex: 2,
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: shadows.md,
						borderRadius: radii.full,
					}}
				>
					<IconArrowLeft size={24} color="#868e96" />
				</ActionIcon>
			</Box>

			<Box px="sm" style={{ marginTop: -50 }}>
				{/* ── Compact Profile Info Card ── */}
				<Card
					radius={radii.lg}
					p="md"
					style={{
						boxShadow: shadows.md,
						position: "relative",
						overflow: "visible",
						zIndex: 10,
					}}
				>
					<Stack align="center" gap={8}>
						{/* Avatar */}
						<Box style={{ position: "relative", marginTop: -40 }}>
							<Box
								style={{
									width: 80,
									height: 80,
									borderRadius: radii.full,
									padding: 3,
									background: "white",
									boxShadow: shadows.md,
								}}
							>
								<Avatar
									src={seller.logo_url}
									size={74}
									radius={37}
									color="blue.6"
								>
									<Text
										fw={800}
										size="24px"
										c="white"
										style={{ fontFamily: "Outfit, sans-serif" }}
									>
										{seller.company_name?.[0]?.toUpperCase() || "?"}
									</Text>
								</Avatar>
							</Box>
							{seller.is_verified && (
								<Box
									style={{
										position: "absolute",
										bottom: 2,
										right: 2,
										background: "#228be6",
										borderRadius: radii.full,
										padding: 2,
										border: "2px solid white",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconShieldCheck size={14} color="white" />
								</Box>
							)}
						</Box>

						{/* Name and Description */}
						<Box ta="center" mt={4}>
							<Text
								fw={800}
								size="20px"
								style={{
									fontFamily: "Outfit, sans-serif",
									letterSpacing: "-0.3px",
								}}
								lh={1.2}
							>
								{seller.company_name || "Seller"}
							</Text>
							{seller.is_verified && (
								<Badge
									color="blue"
									variant="light"
									size="sm"
									mt={4}
									radius="sm"
									fw={800}
								>
									VERIFIED SELLER
								</Badge>
							)}
							{seller.description && (
								<Text
									size="12px"
									c="dimmed"
									mt={8}
									lh={1.4}
									maw={280}
									mx="auto"
								>
									{seller.description}
								</Text>
							)}
						</Box>

						{/* Action Buttons */}
						<Group wrap="nowrap" w="100%" mt={12} gap="xs">
							{seller.phone ? (
								<Button
									radius={radii.md}
									size="sm"
									color="blue"
									style={{ flex: 1, boxShadow: shadows.accent }}
									leftSection={<IconPhone size={16} />}
									component="a"
									href={`tel:${seller.phone}`}
								>
									Call
								</Button>
							) : seller.telegram_username ? (
								<Button
									radius={radii.md}
									size="sm"
									color="blue"
									style={{ flex: 1, boxShadow: shadows.accent }}
									leftSection={<IconBrandTelegram size={16} />}
									component="a"
									href={`https://t.me/${seller.telegram_username}`}
									target="_blank"
								>
									Message on Telegram
								</Button>
							) : (
								<Button
									radius={radii.md}
									size="sm"
									color="blue"
									style={{ flex: 1, boxShadow: shadows.accent }}
									leftSection={<IconPhone size={16} />}
									disabled
								>
									No Contact
								</Button>
							)}

							{seller.phone && seller.telegram_username && (
								<ActionIcon
									radius={radii.md}
									size={36}
									variant="light"
									color="blue"
									component="a"
									href={`https://t.me/${seller.telegram_username}`}
									target="_blank"
								>
									<IconBrandTelegram size={18} />
								</ActionIcon>
							)}
							<ActionIcon
								radius={radii.md}
								size={36}
								variant="default"
								onClick={handleShare}
								style={{
									border: "1px solid #e2e8f0",
									background: surface.page,
									color: "#64748b",
								}}
							>
								<IconShare size={18} />
							</ActionIcon>
						</Group>

						{/* Compact Stats Row */}
						<Group grow w="100%" mt={8} gap="xs">
							<Stack
								gap={2}
								align="center"
								py="xs"
								style={{ backgroundColor: surface.page, borderRadius: radii.md, border: "1px solid #f1f5f9" }}
							>
								<ThemeIcon variant="light" color="blue" size="sm" radius="md">
									<IconList size={14} />
								</ThemeIcon>
								<Text
									fw={800}
									size="16px"
									c="dark.9"
									mt={2}
									lh={1}
									style={{ fontFamily: "Outfit, sans-serif" }}
								>
									{seller.listings_count}
								</Text>
								<Text
									size="9px"
									c="dimmed"
									fw={700}
									tt="uppercase"
									style={{ letterSpacing: 0.5 }}
								>
									Listings
								</Text>
							</Stack>
							<Stack
								gap={2}
								align="center"
								py="xs"
								style={{ backgroundColor: surface.page, borderRadius: radii.md, border: "1px solid #f1f5f9" }}
							>
								<ThemeIcon variant="light" color="teal" size="sm" radius="md">
									<IconCalendarEvent size={14} />
								</ThemeIcon>
								<Text
									fw={800}
									size="16px"
									c="dark.9"
									mt={2}
									lh={1}
									style={{ fontFamily: "Outfit, sans-serif" }}
								>
									{yearsActive}+
								</Text>
								<Text
									size="9px"
									c="dimmed"
									fw={700}
									tt="uppercase"
									style={{ letterSpacing: 0.5 }}
								>
									Years
								</Text>
							</Stack>
							<Stack
								gap={2}
								align="center"
								py="xs"
								style={{ backgroundColor: surface.page, borderRadius: radii.md, border: "1px solid #f1f5f9" }}
							>
								<ThemeIcon variant="light" color="violet" size="sm" radius="md">
									<IconEye size={14} />
								</ThemeIcon>
								<Text
									fw={800}
									size="16px"
									c="dark.9"
									mt={2}
									lh={1}
									style={{ fontFamily: "Outfit, sans-serif" }}
								>
									{totalViews}
								</Text>
								<Text
									size="9px"
									c="dimmed"
									fw={700}
									tt="uppercase"
									style={{ letterSpacing: 0.5 }}
								>
									Views
								</Text>
							</Stack>
						</Group>
					</Stack>
				</Card>

				{/* ── Social Links Section ── */}
				{(seller.instagram_url || seller.website_url) && (
					<Box mt={24}>
						<Text fw={700} size="sm" mb="xs" c="dark.8">
							Connect
						</Text>
						<Stack gap="xs">
							{seller.instagram_url && (
								<Card
									component="a"
									href={seller.instagram_url}
									target="_blank"
									radius={radii.md}
									p="sm"
									style={{
										display: "flex",
										alignItems: "center",
										transition: "all 0.2sease",
										textDecoration: "none",
										background: "white",
										border: "1px solid #f1f5f9",
										boxShadow: shadows.md,
									}}
								>
									<ThemeIcon size={32} radius="md" color="pink" variant="light">
										<IconBrandInstagram size={18} />
									</ThemeIcon>
									<Box ml="sm" style={{ flex: 1 }}>
										<Text fw={600} size="13px" c="dark.8">
											Instagram
										</Text>
										<Text size="11px" c="dimmed">
											{seller.instagram_url
												.replace(/https?:\/\/(www\.)?instagram\.com\//, "@")
												.replace(/\/$/, "") || "View profile"}
										</Text>
									</Box>
									<IconChevronRight size={16} color="#cbd5e1" />
								</Card>
							)}
							{seller.website_url && (
								<Card
									component="a"
									href={seller.website_url}
									target="_blank"
									radius={radii.md}
									p="sm"
									style={{
										display: "flex",
										alignItems: "center",
										transition: "all 0.2sease",
										textDecoration: "none",
										background: "white",
										border: "1px solid #f1f5f9",
										boxShadow: shadows.md,
									}}
								>
									<ThemeIcon size={32} radius="md" color="gray" variant="light">
										<IconWorld size={18} />
									</ThemeIcon>
									<Box ml="sm" style={{ flex: 1 }}>
										<Text fw={600} size="13px" c="dark.8">
											Website
										</Text>
										<Text size="11px" c="dimmed">
											{seller.website_url
												.replace(/https?:\/\/(www\.)?/, "")
												.replace(/\/$/, "")}
										</Text>
									</Box>
									<IconChevronRight size={16} color="#cbd5e1" />
								</Card>
							)}
						</Stack>
					</Box>
				)}

				{/* ── Listings Section ── */}
				<Box mt={24} mb={40}>
					<Group justify="space-between" align="center" mb="sm">
						<Group gap={6}>
							<ThemeIcon variant="light" color="blue" size="sm" radius="md">
								<IconBuilding size={14} />
							</ThemeIcon>
							<Text
								fw={800}
								size="18px"
								c="dark.9"
								style={{
									fontFamily: "Outfit, sans-serif",
									letterSpacing: "-0.3px",
								}}
							>
								Properties
							</Text>
						</Group>
						<Badge
							size="xs"
							variant="dot"
							color="blue"
							style={{ background: surface.page, fontWeight: 800 }}
						>
							{listings.length} ACTIVE
						</Badge>
					</Group>

					{listings.length > 0 ? (
						<div className="listings-uniform-grid">
							{listings.map((item) => (
								<ListingCard
									key={item.id}
									listing={item}
									onClick={(listingId) => navigate(`/listings/${listingId}`)}
								/>
							))}
						</div>
					) : (
						<Paper
							p="xl"
							radius={radii.lg}
							ta="center"
							style={{ backgroundColor: surface.page, border: "1px dashed #cbd5e1" }}
						>
							<IconHome2
								size={32}
								color="#94a3b8"
								stroke={1.5}
								style={{ margin: "0 auto 8px" }}
							/>
							<Text fw={600} size="sm" c="dark.7">
								No properties yet
							</Text>
							<Text size="12px" c="dimmed" mt={4}>
								This seller hasn't posted any listings.
							</Text>
						</Paper>
					)}
				</Box>
			</Box>
		</Container>
	);
}

export const SellerProfile = {
	route: "/seller/:id",
	Page,
};
