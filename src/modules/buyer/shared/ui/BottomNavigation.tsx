import { useRef, useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Avatar, Box, UnstyledButton } from "@mantine/core";
import {
	IconHome,
	IconSearch,
	IconHeart,
	IconHeartFilled,
	IconUser,
	IconUserFilled,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { $userStats } from "@shared/state/user/model";
import { clearFilters } from "@modules/buyer/shared/state/model";
import { useAuth } from "@app/providers/useAuth";
import { NavTab, type NavItem } from "./NavTab";
import { radii, shadows } from "@app/styles/theme";

const PILL_ITEMS: NavItem[] = [
	{ icon: IconHome, labelKey: "nav.home", path: "/", badgeKey: null },
	{
		icon: IconHeart,
		filledIcon: IconHeartFilled,
		labelKey: "nav.favorites",
		path: "/favorites",
		badgeKey: "favoritesCount",
	},
	{
		icon: IconUser,
		filledIcon: IconUserFilled,
		labelKey: "nav.settings",
		path: "/profile",
		badgeKey: null,
	},
];

const SEARCH_ITEM: NavItem = {
	icon: IconSearch,
	labelKey: "nav.search",
	path: "/search",
	badgeKey: null,
};

interface BottomNavigationProps {
	onSearchToggle?: () => void;
	searchOpen?: boolean;
}

export function BottomNavigation({
	onSearchToggle,
	searchOpen = false,
}: BottomNavigationProps) {
	const { t } = useTranslation("buyer");
	const location = useLocation();
	const navigate = useNavigate();
	const userStats = useUnit($userStats);
	const { user } = useAuth();

	// Build user avatar for settings tab
	const getInitials = () => {
		if (!user) return "";
		const first = user.first_name?.[0] || "";
		const last = user.last_name?.[0] || "";
		return (first + last).toUpperCase() || "";
	};

	const userAvatar = user ? (
		<Avatar
			src={user.avatar_url}
			size={26}
			radius={radii.full}
			color="blue"
			style={{
				border: "2px solid transparent",
			}}
		>
			{getInitials()}
		</Avatar>
	) : null;

	const pillRef = useRef<HTMLDivElement>(null);
	const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
	const [indicator, setIndicator] = useState({ left: 0, width: 0 });

	const isActivePath = (path: string): boolean => {
		if (path === "/favorites") return location.pathname === "/favorites";
		if (path === "/search") return searchOpen;
		if (path === "/") return location.pathname === "/" && !searchOpen;
		if (path === "/profile") {
			return [
				"/profile",
				"/edit-profile",
				"/preferences",
				"/notifications",
				"/become-seller",
				"/about",
				"/faq",
				"/support",
				"/privacy",
				"/terms",
				"/for-realtors",
				"/seller/",
			].some((p) => location.pathname.startsWith(p));
		}
		return location.pathname.startsWith(path);
	};

	const activeIndex = PILL_ITEMS.findIndex((item) => isActivePath(item.path));

	const updateIndicator = useCallback(() => {
		const pill = pillRef.current;
		const tab = tabRefs.current[activeIndex];
		if (!pill || !tab || activeIndex < 0) return;

		const pillRect = pill.getBoundingClientRect();
		const slotWidth = pillRect.width / PILL_ITEMS.length;
		setIndicator({
			left: Math.round(activeIndex * slotWidth) + 2,
			width: Math.round(slotWidth) - 4,
		});
	}, [activeIndex]);

	useEffect(() => {
		updateIndicator();
	}, [updateIndicator]);

	const getBadgeValue = (
		key: "favoritesCount" | "unreadCount" | null,
	): number => {
		if (!key || !userStats) return 0;
		return userStats[key] || 0;
	};

	const handleTabClick = (item: NavItem) => {
		if (item.path === "/") {
			clearFilters();
			navigate("/");
		} else if (item.path === "/search") {
			onSearchToggle?.();
		} else {
			navigate(item.path);
		}
	};

	return (
		<Box
			component="nav"
			style={{
				position: "fixed",
				bottom: 0,
				left: 0,
				right: 0,
				paddingBottom: "env(safe-area-inset-bottom, 0px)",
				zIndex: 10000,
				pointerEvents: "none",
			}}
		>
			<Box
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					padding: "4px 12px 12px",
					maxWidth: 500,
					margin: "0 auto",
				}}
			>
				{/* Main tab bar — pill with border + blur */}
				<Box
					ref={pillRef}
					style={{
						display: "flex",
						alignItems: "center",
						flex: 1,
						height: 56,
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						borderRadius: radii.full,
						padding: "5px 0",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: shadows.md,
						pointerEvents: "auto",
						marginRight: 10,
						position: "relative",
						overflow: "hidden",
					}}
				>
					{/* Sliding active indicator — moves behind active tab */}
					{activeIndex >= 0 && indicator.width > 0 && (
						<Box
							style={{
								position: "absolute",
								top: 2,
								left: indicator.left,
								width: indicator.width,
								height: "calc(100% - 4px)",
								borderRadius: 30,
								backgroundColor: "rgba(34, 139, 230, 0.1)",
								transition: "0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
								pointerEvents: "none",
							}}
						/>
					)}

					{PILL_ITEMS.map((item, i) => (
						<NavTab
							key={item.path}
							ref={(el) => {
								tabRefs.current[i] = el;
							}}
							item={item}
							isActive={isActivePath(item.path)}
							badgeValue={getBadgeValue(item.badgeKey)}
							onClick={() => handleTabClick(item)}
							t={t}
							customIcon={item.path === "/profile" ? userAvatar : undefined}
						/>
					))}
				</Box>

				{/* Search button — circle with border + blur */}
				<UnstyledButton
					onClick={() => handleTabClick(SEARCH_ITEM)}
					style={{
						width: 56,
						height: 56,
						borderRadius: "50%",
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: shadows.md,
						pointerEvents: "auto",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						flexShrink: 0,
					}}
				>
					<IconSearch
						size={24}
						stroke={isActivePath("/search") ? 2.2 : 1.6}
						color={isActivePath("/search") ? "#228be6" : "#868e96"}
					/>
				</UnstyledButton>
			</Box>
		</Box>
	);
}
