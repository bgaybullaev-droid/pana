import { sample } from 'effector';
import { authenticateWithTelegramFx, devLoginFx, checkSessionFx, logoutFx } from '../../../auth/model/effects';
import { fetchUserStats, startPolling, stopPolling } from '../events';
import { fetchUserStatsFx } from '../effects';
import { $userStats } from '../stores';

// Store wiring
$userStats
  .on(fetchUserStatsFx.doneData, (_, stats) => stats)
  .reset(logoutFx.done);

// Fetch stats when event fires
sample({
  clock: fetchUserStats,
  target: fetchUserStatsFx,
});

// Fetch stats automatically after successful authentication, then start polling
sample({
  clock: authenticateWithTelegramFx.done,
  target: fetchUserStatsFx,
});

sample({
  clock: devLoginFx.done,
  target: fetchUserStatsFx,
});

// Also start polling when session is restored from existing cookie
sample({
  clock: checkSessionFx.done,
  target: fetchUserStatsFx,
});

// Start polling after first successful fetch
sample({
  clock: fetchUserStatsFx.done,
  target: startPolling,
});

// Polling logic (30 second interval)
let pollInterval: ReturnType<typeof setInterval> | null = null;

startPolling.watch(() => {
  if (pollInterval) return; // already polling
  pollInterval = setInterval(() => {
    fetchUserStatsFx();
  }, 30_000);
});

stopPolling.watch(() => {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
});

// Stop polling and clear stats on logout
logoutFx.done.watch(() => {
  stopPolling();
});
