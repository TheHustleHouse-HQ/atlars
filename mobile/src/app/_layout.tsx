import { useEffect, useState } from "react";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { getRefreshToken, setAccessToken, setRefreshToken } from "@/lib/auth";
import { apiRequest, AuthResponse } from "@/lib/api";

export default function RootLayout() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // On app launch, try to silently restore session from stored refresh token
    async function restoreSession() {
      try {
        const refreshToken = await getRefreshToken();
        if (refreshToken) {
          const data = await apiRequest<AuthResponse>("/auth/refresh", {
            method: "POST",
            authenticated: false,
          });
          setAccessToken(data.access_token);
          await setRefreshToken(data.refresh_token);
          router.replace("/(tabs)/dashboard");
        } else {
          router.replace("/(auth)/login");
        }
      } catch {
        router.replace("/(auth)/login");
      } finally {
        setReady(true);
      }
    }

    restoreSession();
  }, []);

  if (!ready) return null;

  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
