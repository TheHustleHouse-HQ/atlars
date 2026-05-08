import { Tabs } from "expo-router";
import { Text } from "react-native";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: "#0a0a0a", borderTopColor: "#1a1a1a" },
        tabBarActiveTintColor: "#fff",
        tabBarInactiveTintColor: "#444",
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{ title: "Dashboard", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>◈</Text> }}
      />
      <Tabs.Screen
        name="journal"
        options={{ title: "Journal", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>✦</Text> }}
      />
      <Tabs.Screen
        name="insights"
        options={{ title: "Insights", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>◉</Text> }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: "Profile", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>◎</Text> }}
      />
    </Tabs>
  );
}
