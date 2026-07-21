import { useEffect, useState } from 'react';
import NetInfo from '@react-native-community/netinfo';

export function useNetworkState() {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isOffline, setIsOffline] = useState<boolean>(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      // isConnected can be null. We treat it as true if null (assume optimistic)
      const connected = state.isConnected ?? true;
      setIsOnline(connected);
      setIsOffline(!connected);
    });

    return () => unsubscribe();
  }, []);

  return { isOnline, isOffline };
}
