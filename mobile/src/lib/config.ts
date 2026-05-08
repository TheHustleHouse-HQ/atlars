// Switch this to your machine's local IP when testing on a physical device
// e.g. "http://192.168.1.42:8000"
// In production EAS builds this is overridden by an environment variable.
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
