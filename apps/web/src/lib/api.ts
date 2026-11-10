export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const KEY = "factor_token";

export const tokenStore = {
  get(): string | null {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  set(token: string) {
    try { localStorage.setItem(KEY, token); } catch { /* storage unavailable */ }
  },
  clear() {
    try { localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function messageFrom(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : ""))
      .filter(Boolean)
      .join(". ");
  }
  return "Something went wrong";
}

type Options = { method?: string; body?: unknown; auth?: boolean };

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth !== false) {
    const token = tokenStore.get();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the API running?");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(data?.detail));
  return data as T;
}

export type Membership = { business_id: number; role: string; status: string };
export type Me = { id: number; email: string; name: string; memberships: Membership[] };
export type Business = {
  id: number;
  name: string;
  upi_id: string | null;
  language: string;
  template: string;
  your_role: string;
  your_permissions: string[];
  business_code?: string | null;
};
export type Member = {
  id: number;
  user_id: number;
  name: string;
  email: string;
  role: string;
  status: string;
  permissions: string[];
};

export type CatalogItem = {
  id: number;
  name: string;
  kind: "ready_stock" | "made_to_order";
  price_paise: number;
  quantity: number | null;
  capacity: number | null;
  lead_time_days: number | null;
  active: boolean;
  available: number;
};
export type OrderSummary = {
  id: number;
  code: string;
  status: string;
  payment_status: string;
  source: string;
  total_paise: number;
  customer_name: string;
  created_at: string;
  linked_conversation_id?: number | null;
  tracking?: CourierTracking | null;
};
export type CourierTracking = {
  id: number; courier_name: string; awb: string; tracking_url: string | null;
  status: string; status_detail: string; updated_at: string; courier_connection_id: number | null;
};
export type OrderDetail = OrderSummary & {
  note: string;
  customer: { id: number; name: string; phone: string | null; handle: string | null };
  items: { name: string; quantity: number; unit_price_paise: number }[];
  events: { kind: string; detail: string; created_at: string }[];
  next_statuses: string[];
  tracking?: CourierTracking | null;
  linked_conversation?: { id: number; channel: string; display_name: string } | null;
  payment?: PaymentInfo;
};
export type PaymentInfo = {
  upi_ready: boolean;
  payee_name: string;
  upi_id: string | null;
  amount_paise: number;
  upi_uri: string | null;
  payment_link: string | null;
  qr_path: string | null;
};
export type PendingPayment = PaymentInfo & {
  id: number; code: string; status: string; payment_status: string;
  total_paise: number; customer_name: string; created_at: string;
};
export type Customer = {
  id: number;
  name: string;
  phone: string | null;
  handle: string | null;
  orders: number;
  spent_paise: number;
};
export type Conversation = {
  id: number;
  channel: "instagram" | "whatsapp";
  handle: string;
  display_name: string;
  status: "agent" | "needs_owner" | "resolved";
  reason: string;
  last_message_at: string;
  last_preview: string;
};
export type ConversationDetail = Conversation & {
  messages: { id: number; direction: "in" | "out"; sender: "customer" | "agent" | "owner"; text: string; created_at: string }[];
  orders: { id: number; code: string; status: string; total_paise: number; created_at?: string; payment?: PaymentInfo; tracking?: CourierTracking | null }[];
};
export type InboxCounts = { needs_owner: number; agent: number; resolved: number };
export type Dashboard = {
  sales_month_paise: number;
  sales_prev_month_paise: number;
  orders_to_fulfil: number;
  ready_to_ship: number;
  in_progress: number;
  unpaid_count: number;
  unpaid_paise: number;
  messages_open: number;
  agent_handled: number;
  daily: { date: string; total_paise: number }[];
  todo: { kind: string; title: string; detail: string; href: string }[];
  customers: number;
};
export type Channel = { id: number; channel: "instagram" | "whatsapp"; label: string; verify_token: string; webhook_path: string };

export type VoiceOrderResult = {
  success: boolean;
  provider: string;
  transcript: string;
  language: string;
  parsed: {
    raw_text: string;
    customer: { name: string; phone: string | null; handle: string | null };
    items: { name: string; quantity: number; unit_price_paise: number; total_paise: number }[];
    total_price_paise: number;
    source: string;
    confidence: number;
  };
  order: {
    id: number;
    code: string;
    status: string;
    payment_status: string;
    total_paise: number;
    customer_name: string;
    created_at: string;
  };
};
