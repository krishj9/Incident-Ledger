import { AppState, AppStateStatus } from 'react-native';
import * as TaskManager from 'expo-task-manager';
import * as BackgroundFetch from 'expo-background-fetch';
import * as Network from 'expo-network';
import { processQueue } from './engine';

const SYNC_TASK_NAME = 'INCIDENT_LEDGER_BACKGROUND_SYNC';

// 1. Define the background task
TaskManager.defineTask(SYNC_TASK_NAME, async () => {
  try {
    const network = await Network.getNetworkStateAsync();
    if (network.isConnected) {
      await processQueue();
      return BackgroundFetch.BackgroundFetchResult.NewData;
    }
    return BackgroundFetch.BackgroundFetchResult.NoData;
  } catch (error) {
    console.error('Background sync failed:', error);
    return BackgroundFetch.BackgroundFetchResult.Failed;
  }
});

// 2. Register background fetch opportunistically
export async function registerBackgroundSync() {
  try {
    await BackgroundFetch.registerTaskAsync(SYNC_TASK_NAME, {
      minimumInterval: 15 * 60, // 15 minutes
      stopOnTerminate: false, // Android only
      startOnBoot: true,      // Android only
    });
  } catch (err) {
    console.warn('Failed to register background sync task:', err);
  }
}

// 3. Setup foreground & network triggers
export function initSyncTriggers() {
  // Run on launch
  Network.getNetworkStateAsync().then(state => {
    if (state.isConnected) {
      processQueue();
    }
  });

  // Run on app foreground
  let appState = AppState.currentState;
  AppState.addEventListener('change', async (nextAppState: AppStateStatus) => {
    if (appState.match(/inactive|background/) && nextAppState === 'active') {
      const state = await Network.getNetworkStateAsync();
      if (state.isConnected) {
        processQueue();
      }
    }
    appState = nextAppState;
  });

  // We can't easily listen to global network reachability changes reliably 
  // via react-native-community/netinfo or expo-network without a hook in a component.
  // Instead, the UI layer (useNetworkState) or explicit Retry actions can invoke processQueue().
}
