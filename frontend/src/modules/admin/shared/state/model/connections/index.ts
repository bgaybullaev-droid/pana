import { sample } from 'effector';
import { getApiError } from '@shared/api/client';
import {
  fetchDashboardStats,
  fetchUsers,
  fetchUserDetail,
  approveUser,
  rejectUser,
  fetchListings,
  fetchListingDetail,
  approveListing,
  rejectListing,
  resetUserDetail,
  resetListingDetail,
} from '../events';
import {
  fetchDashboardStatsFx,
  fetchUsersFx,
  fetchUserDetailFx,
  approveUserFx,
  rejectUserFx,
  fetchListingsFx,
  fetchListingDetailFx,
  approveListingFx,
  rejectListingFx,
} from '../effects';
import {
  $dashboardStats,
  $isLoadingDashboard,
  $users,
  $usersPagination,
  $isLoadingUsers,
  $selectedUser,
  $isLoadingUserDetail,
  $listings,
  $listingsPagination,
  $isLoadingListings,
  $selectedListing,
  $isLoadingListingDetail,
  $adminError,
} from '../stores';

// Dashboard store wiring
$dashboardStats.on(
  fetchDashboardStatsFx.doneData,
  (_, stats) => stats
);

$isLoadingDashboard.on(
  fetchDashboardStatsFx.pending,
  (_, pending) => pending
);

// Users store wiring
$users.on(
  fetchUsersFx.doneData,
  (_, response) => response.items
);

$usersPagination.on(fetchUsersFx.doneData, (_, response) => ({
  page: response.page,
  perPage: response.per_page,
  total: response.total,
  totalPages: response.total_pages,
}));

$isLoadingUsers.on(
  fetchUsersFx.pending,
  (_, pending) => pending
);

$selectedUser
  .on(fetchUserDetailFx.doneData, (_, user) => user)
  .on(approveUserFx.doneData, (_, user) => user)
  .on(rejectUserFx.doneData, (_, user) => user)
  .reset(resetUserDetail);

$isLoadingUserDetail
  .on(fetchUserDetailFx.pending, (_, pending) => pending)
  .on(approveUserFx.pending, (_, pending) => pending)
  .on(rejectUserFx.pending, (_, pending) => pending);

// Listings store wiring
$listings.on(
  fetchListingsFx.doneData,
  (_, response) => response.items
);

$listingsPagination.on(fetchListingsFx.doneData, (_, response) => ({
  page: response.page,
  perPage: response.per_page,
  total: response.total,
  totalPages: response.total_pages,
}));

$isLoadingListings.on(
  fetchListingsFx.pending,
  (_, pending) => pending
);

$selectedListing
  .on(fetchListingDetailFx.doneData, (_, listing) => listing)
  .on(approveListingFx.doneData, (_, listing) => listing)
  .on(rejectListingFx.doneData, (_, listing) => listing)
  .reset(resetListingDetail);

$isLoadingListingDetail
  .on(fetchListingDetailFx.pending, (_, pending) => pending)
  .on(approveListingFx.pending, (_, pending) => pending)
  .on(rejectListingFx.pending, (_, pending) => pending);

// Errors store wiring
$adminError
  .on(fetchUsersFx.failData, (_, error) => getApiError(error).message)
  .on(approveUserFx.failData, (_, error) => getApiError(error).message)
  .on(rejectUserFx.failData, (_, error) => getApiError(error).message)
  .on(fetchListingsFx.failData, (_, error) => getApiError(error).message)
  .on(approveListingFx.failData, (_, error) => getApiError(error).message)
  .on(rejectListingFx.failData, (_, error) => getApiError(error).message)
  .reset(fetchUsersFx)
  .reset(fetchListingsFx);

// Sample connections
sample({ clock: fetchDashboardStats, target: fetchDashboardStatsFx });
sample({ clock: fetchUsers, target: fetchUsersFx });
sample({ clock: fetchUserDetail, target: fetchUserDetailFx });
sample({ clock: approveUser, target: approveUserFx });
sample({ clock: rejectUser, target: rejectUserFx });
sample({ clock: fetchListings, target: fetchListingsFx });
sample({ clock: fetchListingDetail, target: fetchListingDetailFx });
sample({ clock: approveListing, target: approveListingFx });
sample({ clock: rejectListing, target: rejectListingFx });
