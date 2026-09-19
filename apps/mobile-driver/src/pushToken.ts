import AsyncStorage from "@react-native-async-storage/async-storage";

const TOKEN_KEY = "porterchain.driver.push_token";

export async function rememberPushToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function readRememberedPushToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function clearRememberedPushToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY);
}
