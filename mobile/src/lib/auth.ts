import * as SecureStore from "expo-secure-store";

const REFRESH_TOKEN_KEY = "atlars_refresh_token";

// Access token lives only in memory — never persisted to disk
let _accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

export async function setRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function clearTokens(): Promise<void> {
  _accessToken = null;
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}
