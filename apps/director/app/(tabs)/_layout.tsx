import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Slot, useRouter } from 'expo-router';
import { useAuth } from '../../src/contexts/AuthContext';
import { colors, spacing, typography } from '../../src/tokens';

export default function TabsLayout() {
  const { user, signOut } = useAuth();
  const router = useRouter();

  const handleSignOut = () => {
    signOut();
    router.replace('/(auth)/sign-in');
  };

  return (
    <View style={styles.container}>
      <View style={styles.appBar}>
        <View style={styles.brand}>
          <Text style={styles.brandText}>Incident Ledger</Text>
          <Text style={styles.portalText}>Director Portal</Text>
        </View>

        <View style={styles.userSection}>
          <View style={styles.userInfo}>
            <Text style={styles.userName}>{user?.display_name || 'Demo Director'}</Text>
            <Text style={styles.userRole}>{user?.role || 'director'}</Text>
          </View>
          <TouchableOpacity onPress={handleSignOut} style={styles.signOutBtn}>
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.content}>
        <Slot />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  appBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.navy,
    paddingHorizontal: spacing.xl,
    height: 64,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.sm,
  },
  brandText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.bold as any,
    color: colors.white,
  },
  portalText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    color: colors.slateLight,
  },
  userSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xl,
  },
  userInfo: {
    alignItems: 'flex-end',
  },
  userName: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold as any,
    color: colors.white,
  },
  userRole: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    color: colors.slateLight,
    textTransform: 'uppercase',
  },
  signOutBtn: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
  },
  signOutText: {
    fontFamily: typography.fontFamily,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium as any,
    color: colors.white,
  },
  content: {
    flex: 1,
  },
});
