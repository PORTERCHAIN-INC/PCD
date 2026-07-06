export { ApiError, parseApiError } from "./errors";
export { createSecurityApi } from "./security";
export {
  createNotificationApi,
  type NotificationApi,
  type NotificationInboxItem,
  type NotificationInboxResponse,
  type NotificationPreference,
} from "./notifications";
export { createApiClient, type ApiClient, type ApiClientConfig } from "./client";
export { createMobileQueryClient } from "./query-client";
export { createDriverApi, type DriverApi } from "./driver";
export type {
  DriverCommunicationsSnapshot,
  DriverDashboard,
  DriverEarningsSnapshot,
  DriverEarningsStatement,
  DriverJobDetail,
  DriverJobSummary,
  DriverJobsList,
  DriverNavigationSession,
  DriverProfile,
  DriverRoute,
  RouteLeg,
  DriverShiftSnapshot,
  DriverTokenResponse,
  NotificationItem,
} from "./driver-types";
export { createCustomerApi, type CustomerApi } from "./customer";
export type {
  AddressPayload,
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
export type {
  OfflineAction,
  OfflineActionRow,
  OfflineActionStatus,
  OfflineQueueAdapter,
  OfflineStatus,
  OfflineSyncAdapter,
  OfflineSyncResult,
  OfflineUploadItem,
  GpsPing,
  ConflictResolution,
} from "./offline";
export { DRIVER_OFFLINE_ACTIONS, CUSTOMER_OFFLINE_ACTIONS, entityKeyForAction } from "./offline";
