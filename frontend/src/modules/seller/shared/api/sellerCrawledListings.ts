import { apiClient } from "@shared/api/client";
import type {
	PaginatedResponse,
	SellerCrawledStats,
	OLXListing,
	TelegramListing,
	Listing,
} from "@shared/api/types";

export async function fetchSellerCrawledStats(): Promise<SellerCrawledStats> {
	const { data } = await apiClient.get<SellerCrawledStats>(
		"/sellers/me/crawled/stats",
	);
	return data;
}

export async function saveSellerPhone(
	phone: string,
): Promise<SellerCrawledStats> {
	const { data } = await apiClient.put<SellerCrawledStats>(
		"/sellers/me/phone",
		{ phone },
	);
	return data;
}

export async function fetchSellerOLXListings(params: {
	page?: number;
	per_page?: number;
	listing_type?: string;
}): Promise<PaginatedResponse<OLXListing>> {
	const { data } = await apiClient.get<PaginatedResponse<OLXListing>>(
		"/sellers/me/crawled/olx",
		{ params },
	);
	return data;
}

export async function fetchSellerTelegramListings(params: {
	page?: number;
	per_page?: number;
	listing_type?: string;
}): Promise<PaginatedResponse<TelegramListing>> {
	const { data } = await apiClient.get<PaginatedResponse<TelegramListing>>(
		"/sellers/me/crawled/telegram",
		{ params },
	);
	return data;
}

export async function claimOlxListing(olxListingId: string): Promise<Listing> {
	const { data } = await apiClient.post<Listing>(
		`/listings/claim-olx/${olxListingId}`,
	);
	return data;
}

export async function claimTelegramListing(
	tgListingId: string,
): Promise<{ listing_id: string; status: string }> {
	const { data } = await apiClient.post<{ listing_id: string; status: string }>(
		`/listings/claim-telegram/${tgListingId}`,
	);
	return data;
}

export async function rejectCrawledListing(
	source: "olx" | "telegram",
	crawledId: string,
): Promise<{ status: string }> {
	const { data } = await apiClient.post<{ status: string }>(
		`/listings/reject-crawled/${source}/${crawledId}`,
	);
	return data;
}
