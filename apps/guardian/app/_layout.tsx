import { Stack } from "expo-router";

/**
 * Root layout for the Incident Ledger Guardian Web App (Expo Web).
 * Token-based acknowledgement flow implemented in Prompt 4.2.
 */
export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Incident Ledger — Guardian" }} />
    </Stack>
  );
}
