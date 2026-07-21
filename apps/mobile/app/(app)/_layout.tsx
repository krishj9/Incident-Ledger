import React from 'react';
import { Tabs } from 'expo-router';
import { View, StyleSheet, SafeAreaView } from 'react-native';
import { ActiveUserBar } from '../../src/components/ActiveUserBar';
import { OfflineBanner } from '../../src/components/OfflineBanner';
import { List, FilePlus2 } from 'lucide-react-native';

export default function AppLayout() {
  return (
    <SafeAreaView style={styles.safeArea}>
      {/* 2. Active user bar (persistent component) */}
      <ActiveUserBar />
      
      {/* 5. Offline banner component */}
      <OfflineBanner />

      <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: '#2563eb' }}>
        <Tabs.Screen
          name="index"
          options={{
            title: 'Incidents',
            tabBarIcon: ({ color, size }) => <List color={color} size={size} />,
          }}
        />
        <Tabs.Screen
          name="report"
          options={{
            title: 'New Report',
            tabBarIcon: ({ color, size }) => <FilePlus2 color={color} size={size} />,
          }}
        />
      </Tabs>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
