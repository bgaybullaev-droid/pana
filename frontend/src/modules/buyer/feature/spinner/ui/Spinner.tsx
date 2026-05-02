import { FC, useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Swiper, SwiperSlide } from "swiper/react";
import { EffectCreative, Virtual } from "swiper/modules";
import type { Swiper as SwiperType } from "swiper";
import { ListingCard } from "./ListingCard";
import type { ListingListItem } from "@shared/api/types";

interface SpinnerProps {
	listings: ListingListItem[];
	onLoadMore: () => void;
	hasMore: boolean;
	isLoading?: boolean;
}

export const Spinner: FC<SpinnerProps> = ({
	listings,
	onLoadMore,
	hasMore,
	isLoading = false,
}) => {
	const { t } = useTranslation("buyer");
	const [activeIndex, setActiveIndex] = useState(0);

	const handleSlideChange = useCallback((swiper: SwiperType) => {
		setActiveIndex(swiper.activeIndex);
	}, []);

	const handleReachEnd = useCallback(() => {
		if (hasMore && !isLoading) {
			onLoadMore();
		}
	}, [hasMore, isLoading, onLoadMore]);

	if (listings.length === 0 && !isLoading) {
		return (
			<div className="flex items-center justify-center h-full">
				<p className="text-gray-500">{t("common.noListings")}</p>
			</div>
		);
	}

	return (
		<Swiper
			direction="vertical"
			effect="creative"
			creativeEffect={{
				prev: { translate: [0, "-100%", 0], opacity: 0 },
				next: { translate: [0, "100%", 0], opacity: 0 },
			}}
			modules={[EffectCreative, Virtual]}
			virtual={{
				enabled: true,
				addSlidesAfter: 2,
				addSlidesBefore: 2,
			}}
			onSlideChange={handleSlideChange}
			onReachEnd={handleReachEnd}
			style={{ height: "100%", width: "100%" }}
		>
			{listings.map((listing, index) => (
				<SwiperSlide key={listing.id} virtualIndex={index}>
					<ListingCard listing={listing} isActive={index === activeIndex} />
				</SwiperSlide>
			))}
		</Swiper>
	);
};
