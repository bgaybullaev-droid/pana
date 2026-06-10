import { createStore } from "effector";
import {
	fetchPhonesFx,
	deletePhoneFx,
	verifyPhoneOtpFx,
	type PhoneRow,
} from "../effects";

export const $phones = createStore<PhoneRow[]>([])
	.on(fetchPhonesFx.doneData, (_, rows) => rows)
	.on(verifyPhoneOtpFx.doneData, (state, row) => [...state, row])
	.on(deletePhoneFx.done, (state, { params }) =>
		state.filter((p) => p.id !== params.phone_id),
	);

export const $isLoadingPhones = createStore<boolean>(false)
	.on(fetchPhonesFx, () => true)
	.on(fetchPhonesFx.finally, () => false);
