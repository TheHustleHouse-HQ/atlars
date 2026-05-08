import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { router } from "expo-router";
import { authApi } from "@/lib/api";

export default function ProfileScreen() {
  async function handleLogout() {
    await authApi.logout();
    router.replace("/(auth)/login");
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.subtitle}>Settings and data export — Phase 5</Text>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Log out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0a0a0a", justifyContent: "center", alignItems: "center", padding: 24 },
  title: { color: "#fff", fontSize: 28, fontWeight: "700", marginBottom: 8 },
  subtitle: { color: "#444", fontSize: 14, textAlign: "center", marginBottom: 40 },
  logoutButton: {
    borderWidth: 1,
    borderColor: "#333",
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 40,
  },
  logoutText: { color: "#ff4444", fontSize: 15, fontWeight: "600" },
});
