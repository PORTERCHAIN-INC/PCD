import type { ApiClient } from "./client";
import { createNotificationApi } from "./notifications";
import type {
  AuthMeResult,
  BookingConfirmationResult,
  BookingConfirmationStatus,
  BookingDraftResult,
  BookingResult,
  CreateQuotePayload,
  CreateSupportPayload,
  CustomerDashboard,
  LiveTrackingPayload,
  OrderResult,
  PaymentRetryResult,
  QuoteResult,
  RebookPayload,
  StartBookingPayload,
  SupportTicket,
} from "./customer-types";

/** Customer / retail API — Porterchain API only (`/v1/*`). Mirrors website/src/lib/api.ts */
export function createCustomerApi(client: ApiClient) {
  const v1 = "/v1";

  return {
    authMe: () => client.get<AuthMeResult>(`${v1}/auth/me`),

    dashboard: () => client.get<CustomerDashboard>(`${v1}/customers/me/dashboard`),

    listSupport: () => client.get<SupportTicket[]>(`${v1}/customers/me/support`),

    createSupport: (body: CreateSupportPayload) =>
      client.post<SupportTicket>(`${v1}/customers/me/support`, body),

    rebook: (orderId: string) =>
      client.post<RebookPayload>(`${v1}/customers/me/rebook/${encodeURIComponent(orderId)}`),

    createQuote: (body: CreateQuotePayload) => client.post<QuoteResult>(`${v1}/quotes`, body),

    getQuote: (quoteId: string) => client.get<QuoteResult>(`${v1}/quotes/${encodeURIComponent(quoteId)}`),

    startBooking: (body: StartBookingPayload) => client.post<BookingResult>(`${v1}/bookings`, body),

    getBookingConfirmation: (quoteId: string) =>
      client.get<BookingConfirmationStatus>(
        `${v1}/bookings/confirmation?quote_id=${encodeURIComponent(quoteId)}`
      ),

    mockCompleteCheckout: (quoteId: string) =>
      client.post<BookingConfirmationResult>(`${v1}/bookings/mock-complete`, { quote_id: quoteId }),

    getOrder: (trackingNumber: string) =>
      client.get<OrderResult>(`${v1}/orders/${encodeURIComponent(trackingNumber)}`),

    getLiveTracking: (trackingNumber: string) =>
      client.get<LiveTrackingPayload>(`${v1}/orders/${encodeURIComponent(trackingNumber)}/tracking`),

    retryPayment: (quoteId: string) =>
      client.post<PaymentRetryResult>(`${v1}/payments/retry`, { quote_id: quoteId }),

    createDraft: (body: {
      session_id: string;
      pickup?: CreateQuotePayload["pickup"];
      dropoff?: CreateQuotePayload["dropoff"];
      vehicle_class?: string;
      package_type?: string;
      weight_kg?: number;
      dimensions?: string;
      current_step?: string;
    }) => client.post<BookingDraftResult>(`${v1}/booking-drafts`, body),

    getActiveDraft: (sessionId: string) =>
      client.get<BookingDraftResult>(`${v1}/booking-drafts/active?session_id=${encodeURIComponent(sessionId)}`),

    getDraft: (draftId: string, sessionId: string) =>
      client.get<BookingDraftResult>(
        `${v1}/booking-drafts/${encodeURIComponent(draftId)}?session_id=${encodeURIComponent(sessionId)}`
      ),

    updateDraft: (
      draftId: string,
      sessionId: string,
      body: {
        pickup?: CreateQuotePayload["pickup"];
        dropoff?: CreateQuotePayload["dropoff"];
        vehicle_class?: string;
        package_type?: string;
        current_step?: string;
      }
    ) =>
      client.patch<BookingDraftResult>(`${v1}/booking-drafts/${encodeURIComponent(draftId)}`, {
        session_id: sessionId,
        ...body,
      }),

    registerPushDevice: (body: {
      fcm_token: string;
      platform: "ios" | "android";
      device_name?: string;
      app_version?: string;
      notification_permission?: boolean;
    }) => client.post<{ device_id: string; registered: boolean }>(`${v1}/notifications/devices/register`, body),

    notificationInbox: (params?: { unreadOnly?: boolean; archived?: boolean }) =>
      createNotificationApi(client, v1).inbox(params),

    notificationHistory: () => createNotificationApi(client, v1).history(),

    markNotificationRead: (id: string) => createNotificationApi(client, v1).markRead(id),

    markNotificationArchive: (id: string) => createNotificationApi(client, v1).markArchive(id),

    markAllNotificationsRead: () => createNotificationApi(client, v1).markAllRead(),

    notificationPreferences: () => createNotificationApi(client, v1).getPreferences(),

    updateNotificationPreference: (body: {
      category: string;
      email_enabled?: boolean;
      push_enabled?: boolean;
      sms_enabled?: boolean;
      in_app_enabled?: boolean;
    }) => createNotificationApi(client, v1).updatePreference(body),
  };
}

export type CustomerApi = ReturnType<typeof createCustomerApi>;
