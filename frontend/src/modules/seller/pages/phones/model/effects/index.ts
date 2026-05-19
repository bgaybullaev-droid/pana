import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

export type PhoneRow = {
	id: string;
	phone: string;
	is_primary: boolean;
	verification_method: string;
	verified_at: string;
	listings_count: number;
};

export const fetchPhonesFx = createEffect<void, PhoneRow[]>(async () => {
	const res = await apiClient.get<PhoneRow[]>("/sellers/me/phones");
	return res.data;
});

export const requestPhoneOtpFx = createEffect<
	{ phone: string },
	{ expires_in: number; _dev_otp?: string }
>(async ({ phone }) => {
	const res = await apiClient.post("/sellers/me/phones/request-otp", {
		phone,
	});
	return res.data;
});

export const verifyPhoneOtpFx = createEffect<
	{ phone: string; code: string },
	PhoneRow
>(async ({ phone, code }) => {
	const res = await apiClient.post<PhoneRow>(
		"/sellers/me/phones/verify-otp",
		{ phone, code },
	);
	return res.data;
});

export const deletePhoneFx = createEffect<
	{
		phone_id: string;
		action:
			| "transfer_to_primary"
			| "transfer_to_other"
			| "archive_listings";
		target_phone_id?: string;
	},
	{
		status: string;
		affected_listings_count: number;
		action: string;
	}
>(async ({ phone_id, action, target_phone_id }) => {
	const res = await apiClient.delete(`/sellers/me/phones/${phone_id}`, {
		data: { action, target_phone_id },
	});
	return res.data;
});
