import type { NotificationRealtimeEvent } from "./types";

export type NotificationRealtimeOptions = {
  apiBaseUrl: string;
  getAccessToken: () => string | null;
  onEvent: (event: NotificationRealtimeEvent) => void;
  onStatusChange?: (connected: boolean) => void;
  orgId?: string;
  reconnectBaseMs?: number;
  reconnectMaxMs?: number;
};

export class NotificationRealtimeClient {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;
  private paused = false;
  private reconnectAttempt = 0;

  constructor(private readonly options: NotificationRealtimeOptions) {}

  connect(): void {
    if (this.paused) return;
    this.closed = false;
    const token = this.options.getAccessToken();
    if (!token) return;

    const base = this.options.apiBaseUrl.replace(/\/$/, "");
    const qs = new URLSearchParams({ token });
    if (this.options.orgId) qs.set("org_id", this.options.orgId);
    const url = `${base.replace(/^http/, "ws")}/v1/notifications/ws?${qs.toString()}`;

    this.socket?.close();
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.options.onStatusChange?.(true);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(String(event.data)) as Record<string, unknown>;
        if (payload.type === "pong") {
          this.options.onEvent({ type: "pong" });
          return;
        }
        if (payload.type === "notification" && payload.payload) {
          this.options.onEvent({
            type: "notification",
            payload: payload.payload as NotificationRealtimeEvent extends {
              type: "notification";
              payload: infer P;
            }
              ? P
              : never,
          });
          return;
        }
        if (typeof payload.unread_count === "number") {
          this.options.onEvent({ type: "unread_count", count: payload.unread_count });
        }
      } catch {
        // Ignore malformed frames.
      }
    };

    socket.onclose = () => {
      this.options.onStatusChange?.(false);
      if (!this.closed && !this.paused) this.scheduleReconnect();
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  setPaused(paused: boolean): void {
    this.paused = paused;
    if (paused) {
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.socket?.close();
      this.socket = null;
      this.options.onStatusChange?.(false);
      return;
    }
    this.connect();
  }

  isPaused(): boolean {
    return this.paused;
  }

  ping(): void {
    if (this.paused) return;
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send("ping");
    }
  }

  disconnect(): void {
    this.closed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.socket?.close();
    this.socket = null;
    this.options.onStatusChange?.(false);
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const base = this.options.reconnectBaseMs ?? 4000;
    const max = this.options.reconnectMaxMs ?? 60000;
    const delay = Math.min(base * 2 ** this.reconnectAttempt, max);
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }
}
