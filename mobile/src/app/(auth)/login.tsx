import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { authApi } from "@/lib/api";
import { setAccessToken, setRefreshToken } from "@/lib/auth";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setError("");
    setLoading(true);
    try {
      const data = await authApi.login(email.trim(), password);
      setAccessToken(data.access_token);
      await setRefreshToken(data.refresh_token);
      router.replace("/(tabs)/dashboard");
    } catch (e: any) {
      setError(e.message ?? "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text style={styles.logo}>ATLARS</Text>
        <Text style={styles.tagline}>Know yourself over time.</Text>

        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor="#555"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor="#555"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="password"
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#000" />
          ) : (
            <Text style={styles.buttonText}>Log in</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.push("/(auth)/register")}>
          <Text style={styles.link}>Don't have an account? Register</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0a0a0a" },
  inner: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
    gap: 14,
  },
  logo: {
    color: "#fff",
    fontSize: 36,
    fontWeight: "800",
    letterSpacing: 4,
    marginBottom: 4,
  },
  tagline: {
    color: "#555",
    fontSize: 15,
    marginBottom: 24,
  },
  input: {
    backgroundColor: "#161616",
    color: "#fff",
    borderRadius: 10,
    padding: 16,
    fontSize: 15,
    borderWidth: 1,
    borderColor: "#222",
  },
  error: {
    color: "#ff4444",
    fontSize: 13,
  },
  button: {
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 16,
    alignItems: "center",
    marginTop: 6,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#000", fontWeight: "700", fontSize: 15 },
  link: { color: "#555", textAlign: "center", fontSize: 14, marginTop: 8 },
});
