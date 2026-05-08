import { View, Text, StyleSheet } from "react-native";

export default function DashboardScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Dashboard</Text>
      <Text style={styles.subtitle}>Domain scores and focus recommendations — Phase 3</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0a0a0a", justifyContent: "center", alignItems: "center", padding: 24 },
  title: { color: "#fff", fontSize: 28, fontWeight: "700", marginBottom: 8 },
  subtitle: { color: "#444", fontSize: 14, textAlign: "center" },
});
