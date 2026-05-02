import { createStore } from 'effector';
import type { Listing } from '@shared/api/types';

export const $createdListing = createStore<Listing | null>(null);

export const $isCreating = createStore(false);

export const $createError = createStore<string | null>(null);

export const $isUploading = createStore(false);

// Edit listing stores
export const $editingListing = createStore<Listing | null>(null);

export const $isLoadingEdit = createStore(false);

export const $isUpdating = createStore(false);

export const $editError = createStore<string | null>(null);
