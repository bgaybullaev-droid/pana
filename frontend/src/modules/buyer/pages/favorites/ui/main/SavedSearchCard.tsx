import { Box, Text, Group, ActionIcon, Badge } from "@mantine/core";
import { IconSearch, IconX, IconBellRinging, IconBellOff } from "@tabler/icons-react";
import type { SavedSearch } from "@shared/api/types";
import { radii } from "@app/styles/theme";
import { useTranslation } from "react-i18next";
import { translateDistrict, translateRegion } from "@shared/lib/regions";

interface SavedSearchCardProps {
	search: SavedSearch;
	onClick: () => void;
	onDelete: (e: React.MouseEvent) => void;
	onToggleNotifications: (e: React.MouseEvent, enabled: boolean) => void;
}

function capitalize(str: string): string {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function generateTags(search: SavedSearch, t: any): string[] {
    const filters = search.filters;
    const tags: string[] = [];

    if (search.query) {
        tags.push(capitalize(search.query));
    }

    if (filters.property_type) {
        const pt = t(`common.propertyType.${filters.property_type}`, filters.property_type);
        tags.push(capitalize(pt));
    }

    if (filters.deal_type) {
        const dealTypeStr = filters.deal_type === "sell" ? t("common.sell") : t("common.rent");
        tags.push(capitalize(dealTypeStr));
    }

    if (filters.rooms?.length) {
        const roomsStr = filters.rooms.map((r) => r === 0 ? t("common.roomsOption.studio") : `${r} ${t("common.rooms")}`).join(", ");
        tags.push(capitalize(roomsStr));
    }

    if (filters.district) {
        tags.push(capitalize(translateDistrict(filters.district, t)));
    } else if (filters.region) {
        tags.push(capitalize(translateRegion(filters.region, t)));
    }

    if (filters.price_min) {
        const formattedPrice = filters.price_min.toLocaleString('en-US').replace(/,/g, ' ');
        tags.push(t("filter.priceFrom", { price: formattedPrice }));
    }

    if (filters.price_max) {
		const formattedPrice = filters.price_max.toLocaleString('en-US').replace(/,/g, ' ');
        tags.push(t("filter.priceTo", { price: formattedPrice }));
    }

    return tags;
}

export function SavedSearchCard({ search, onClick, onDelete, onToggleNotifications }: SavedSearchCardProps) {
	const { t } = useTranslation('buyer');
    const tags = generateTags(search, t);
    
	const hasNew = search.new_count > 0;
	const newCount = search.new_count;
    
    // By default, assuming notifications are enabled if undefined
    const isNotificationsEnabled = search.notifications_enabled ?? true;

	// Badge styling
	let badgeBg = '#e9ecef';
	let badgeColor = '#495057';
	if (newCount > 0 && newCount <= 20) {
		badgeBg = '#d3f9d8'; // light green
		badgeColor = '#2b8a3e'; // dark green
	} else if (newCount > 20) {
		badgeBg = '#ffec99'; // amber / yellow
		badgeColor = '#b06500'; // dark amber
	}

	return (
		<Box
			onClick={onClick}
            pos="relative"
			style={{
				backgroundColor: "#ffffff",
				borderRadius: radii.md,
				padding: "16px",
				boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
				border: "1px solid #f1f3f5",
				cursor: "pointer",
				transition: "all 0.18s ease",
				opacity: hasNew ? 1 : 0.65, // visually muting cards without new listings
			}}
		>
			<Group wrap="nowrap" gap={14} align="flex-start">
				{/* Icon */}
				<Box
					style={{
						width: 44,
						height: 44,
						borderRadius: 22,
						backgroundColor: hasNew ? "#e7f5ff" : "#f1f3f5",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						flexShrink: 0,
					}}
				>
					<IconSearch size={22} color={hasNew ? "#339af0" : "#adb5bd"} stroke={1.8} />
				</Box>

				{/* Content */}
				<Box style={{ flex: 1, minWidth: 0 }}>
					<Group justify="space-between" wrap="nowrap" align="flex-start" mb={8}>
						{/* Filter Tags */}
						<Box style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flex: 1, marginTop: 4 }}>
							{tags.length > 0 ? tags.map((tag, i) => (
								<Badge 
									key={i} 
									color="blue" 
									variant="filled" 
									size="md" 
									radius="md" 
									style={{ 
										backgroundColor: '#e7f5ff', 
										color: '#1c7ed6', 
										textTransform: 'none', 
										fontWeight: 500,
										border: "none",
									}}
								>
									{tag}
								</Badge>
							)) : (
								<Badge 
									color="gray" 
									variant="filled" 
									size="md" 
									radius="md" 
									style={{ 
										backgroundColor: '#f1f3f5', 
										color: '#868e96', 
										textTransform: 'none', 
										fontWeight: 400,
										border: "none",
									}}
								>
									{t("filter.allListings")}
								</Badge>
							)}
						</Box>

						{/* Delete button */}
						<ActionIcon
							variant="subtle"
							color="gray"
							size="sm"
							radius="xl"
							onClick={onDelete}
							style={{ flexShrink: 0, marginTop: 2, marginLeft: 8 }}
						>
							<IconX size={16} stroke={1.5} />
						</ActionIcon>
					</Group>

					{/* New count & Notifications toggle */}
					<Group gap={8} align="center" wrap="nowrap">
						<Box>
							{hasNew ? (
								<Badge
									size="md"
									radius="sm"
									style={{ 
										backgroundColor: badgeBg, 
										color: badgeColor, 
										textTransform: 'none', 
										fontWeight: 600,
										padding: "4px 8px",
										height: "auto",
										border: "none",
									}}
								>
									{t("favorites.searches.newCountShort", { count: newCount })}
								</Badge>
							) : (
								<Text size="sm" c="dimmed">
									{t("favorites.searches.noNew")}
								</Text>
							)}
						</Box>

						<ActionIcon
							variant="subtle"
							size="md"
							radius="xl"
							color={isNotificationsEnabled ? "yellow" : "gray"}
							onClick={(e) => {
                                e.stopPropagation();
                                onToggleNotifications(e, !isNotificationsEnabled);
                            }}
							title={isNotificationsEnabled ? t("favorites.searches.notificationsOff") : t("favorites.searches.notificationsOn")}
						>
							{isNotificationsEnabled ? (
								<IconBellRinging size={18} stroke={1.5} />
							) : (
								<IconBellOff size={18} stroke={1.5} />
							)}
						</ActionIcon>
					</Group>
				</Box>
			</Group>
            
            {search.id === "__mock_demonstration" && (
                <Text size="11px" c="gray.4" style={{ position: "absolute", bottom: 8, right: 12, pointerEvents: "none" }}>
                    mockup
                </Text>
            )}
		</Box>
	);
}
