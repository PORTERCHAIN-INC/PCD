import type { NavigatorScreenParams } from "@react-navigation/native";

export type AuthStackParamList = {
  SignIn: undefined;
};

export type HomeStackParamList = {
  Home: undefined;
};

export type BookingsStackParamList = {
  Bookings: undefined;
  Quote: { rebookOrderId?: string } | undefined;
  Booking: { quoteId: string };
  BookingDraft: undefined;
  StripeCheckout: { checkoutUrl: string; quoteId: string; mockCheckout?: boolean };
  BookingConfirmation: { quoteId: string };
};

export type TrackingStackParamList = {
  Tracking: { trackingNumber?: string } | undefined;
  LiveMap: { trackingNumber: string };
  History: undefined;
};

export type NotificationsStackParamList = {
  Notifications: undefined;
};

export type ProfileStackParamList = {
  Profile: undefined;
  Invoices: undefined;
  Receipts: undefined;
  Support: undefined;
  Claims: undefined;
  OfflineSync: undefined;
  Settings: undefined;
  Performance: undefined;
};

export type MainTabParamList = {
  Home: NavigatorScreenParams<HomeStackParamList>;
  Bookings: NavigatorScreenParams<BookingsStackParamList>;
  Tracking: NavigatorScreenParams<TrackingStackParamList>;
  Notifications: NavigatorScreenParams<NotificationsStackParamList>;
  Profile: NavigatorScreenParams<ProfileStackParamList>;
};

export type RootStackParamList = {
  SignIn: undefined;
  Main: undefined;
};
