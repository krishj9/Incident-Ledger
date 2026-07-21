import React, { useEffect } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { AuthProvider, useAuth } from '../src/contexts/AuthContext';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { TamaguiProvider } from 'tamagui';
import appConfig from '../tamagui.config';
import { initSyncTriggers, registerBackgroundSync } from '../src/sync/triggers';

// Register background task immediately in global scope
registerBackgroundSync();

function RootLayoutNav() {
  const { token, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    // Initialize foreground/launch sync triggers
    initSyncTriggers();
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!token && !inAuthGroup) {
      // Redirect to sign-in if not authenticated
      router.replace('/(auth)/sign-in');
    } else if (token && inAuthGroup) {
      // Redirect away from sign-in if authenticated
      router.replace('/(app)');
    }
  }, [token, isLoading, segments]);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  return <Slot />;
}

export default function RootLayout() {
  return (
    <TamaguiProvider config={appConfig} defaultTheme="light">
      <AuthProvider>
        <RootLayoutNav />
      </AuthProvider>
    </TamaguiProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
});
