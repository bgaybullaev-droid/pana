import { createStore } from "effector";
import { fetchTariffsStatusFx, type TariffsStatus } from "../effects";

export const $tariffsStatus = createStore<TariffsStatus | null>(null).on(
	fetchTariffsStatusFx.doneData,
	(_, payload) => payload,
);

export const $isLoadingTariffs = createStore<boolean>(false)
	.on(fetchTariffsStatusFx, () => true)
	.on(fetchTariffsStatusFx.finally, () => false);

export const $tariffsError = createStore<string | null>(null)
	.on(fetchTariffsStatusFx, () => null)
	.on(fetchTariffsStatusFx.failData, (_, err) => err.message ?? "error");
