import type { NavigatorScreenParams } from "@react-navigation/native";

export type AuthStackParamList = { SignIn: undefined };

export type HomeStackParamList = { Home: undefined };

export type JobsStackParamList = {
  Jobs: undefined;
  JobDetail: { orderId: string };
  AssignmentQueue: undefined;
  Pod: { orderId: string; routeId: string; stopId: string };
  Incident: { orderId?: string };
};

export type NavigationStackParamList = {
  Navigation: { orderId?: string } | undefined;
  LiveMap: { orderId?: string };
};

export type EarningsStackParamList = { Earnings: undefined };

export type ShiftStackParamList = { Shift: undefined };

export type MoreStackParamList = {
  More: undefined;
  Profile: undefined;
  Notifications: undefined;
  OfflineSync: undefined;
  Support: undefined;
  Sos: undefined;
  Settings: undefined;
  Performance: undefined;
};

export type MainTabParamList = {
  Home: NavigatorScreenParams<HomeStackParamList>;
  Jobs: NavigatorScreenParams<JobsStackParamList>;
  Navigation: NavigatorScreenParams<NavigationStackParamList>;
  Earnings: NavigatorScreenParams<EarningsStackParamList>;
  Shift: NavigatorScreenParams<ShiftStackParamList>;
  More: NavigatorScreenParams<MoreStackParamList>;
};

export type RootStackParamList = {
  SignIn: undefined;
  Main: undefined;
};
