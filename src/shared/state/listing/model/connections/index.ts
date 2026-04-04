import { sample } from 'effector';
import { getApiError } from '@shared/api/client';
import {
  createListing,
  updateListing,
  fetchListingForEdit,
  resetCreateState,
  resetEditState,
} from '../events';
import {
  createListingFx,
  updateListingFx,
  fetchListingForEditFx,
  uploadImageFx,
} from '../effects';
import {
  $createdListing,
  $isCreating,
  $createError,
  $isUploading,
  $editingListing,
  $isLoadingEdit,
  $isUpdating,
  $editError,
} from '../stores';

// =============================================================================
// $createdListing wiring
// =============================================================================

$createdListing
  .on(createListingFx.doneData, (_, listing) => listing)
  .reset(resetCreateState);

// =============================================================================
// $isCreating wiring
// =============================================================================

$isCreating
  .on(createListingFx.pending, (_, pending) => pending);

// =============================================================================
// $createError wiring
// =============================================================================

$createError
  .on(createListingFx.failData, (_, error) => getApiError(error).message)
  .reset(createListingFx)
  .reset(resetCreateState);

// =============================================================================
// $isUploading wiring
// =============================================================================

$isUploading
  .on(uploadImageFx.pending, (_, pending) => pending);

// =============================================================================
// $editingListing wiring
// =============================================================================

$editingListing
  .on(fetchListingForEditFx.doneData, (_, listing) => listing)
  .on(updateListingFx.doneData, (_, listing) => listing)
  .reset(resetEditState);

// =============================================================================
// $isLoadingEdit wiring
// =============================================================================

$isLoadingEdit
  .on(fetchListingForEditFx.pending, (_, pending) => pending);

// =============================================================================
// $isUpdating wiring
// =============================================================================

$isUpdating
  .on(updateListingFx.pending, (_, pending) => pending);

// =============================================================================
// $editError wiring
// =============================================================================

$editError
  .on(fetchListingForEditFx.failData, (_, error) => getApiError(error).message)
  .on(updateListingFx.failData, (_, error) => getApiError(error).message)
  .reset(fetchListingForEditFx)
  .reset(updateListingFx)
  .reset(resetEditState);

// =============================================================================
// Sample connections
// =============================================================================

sample({
  clock: createListing,
  target: createListingFx,
});

sample({
  clock: updateListing,
  target: updateListingFx,
});

sample({
  clock: fetchListingForEdit,
  target: fetchListingForEditFx,
});
