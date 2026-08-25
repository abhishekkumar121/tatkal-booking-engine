const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const WS_BASE = BASE.replace(/^http/, "ws");

export interface FlashSale {
  id: number;
  product_id: number;
  start_time: string;
  end_time: string;
  max_per_user: number;
  status: string;
}

export interface FlashSaleStatus {
  id: number;
  status: "scheduled" | "live" | "ended";
  product_id: number;
  start_time: string;
  end_time: string;
}

export interface Product {
  id: number;
  name: string;
  price: string;
  total_stock: number;
}

export interface Order {
  id: number;
  user_id: number;
  flash_sale_id: number;
  quantity: number;
  status: string;
  refund_status?: string | null;
  berth_preference?: string | null;
  passenger_names?: string | null;
}

export interface QueueStatus {
  status: "allowed" | "queued" | "not_in_queue";
  position?: number;
  message?: string;
}

export interface FlashSaleWithProduct {
  id: number;
  product_id: number;
  product_name: string;
  price: string;
  total_stock: number;
  start_time: string;
  end_time: string;
  status: string;
  max_per_user: number;
}

type ApiValidationDetail = {
  msg?: string;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const data = await res.json();
  if (!res.ok) {
    let message = "Request failed";
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail
        .map((d: ApiValidationDetail) => d.msg || JSON.stringify(d))
        .join(", ");
    } else if (data.detail) {
      message = JSON.stringify(data.detail);
    }
    throw new Error(message);
  }
  return data as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<{ id: number; email: string; message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  verifyEmail: (email: string, code: string) =>
    request<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ email, code }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listFlashSales: () => request<FlashSale[]>("/flash-sales/"),
  listFlashSalesDetailed: () =>
    request<FlashSaleWithProduct[]>("/flash-sales/with-details"),

  getFlashSale: (id: number) => request<FlashSale>(`/flash-sales/${id}`),

  getFlashSaleStatus: (id: number) =>
    request<FlashSaleStatus>(`/flash-sales/${id}/status`),

  getProduct: (id: number) => request<Product>(`/products/${id}`),

  joinQueue: (flashSaleId: number, token: string) =>
    request<QueueStatus>(`/queue/${flashSaleId}/join`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }),

  checkPosition: (flashSaleId: number, token: string) =>
    request<QueueStatus>(`/queue/${flashSaleId}/position`, {
      headers: { Authorization: `Bearer ${token}` },
    }),

  createOrder: (
    flashSaleId: number,
    quantity: number,
    token: string,
    berthPreference: string,
    passengerNames: string,
  ) =>
    request<Order>("/orders/", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        flash_sale_id: flashSaleId,
        quantity,
        idempotency_key: crypto.randomUUID(),
        berth_preference: berthPreference,
        passenger_names: passengerNames,
      }),
    }),

  payOrder: (orderId: number, simulateFailure: boolean, token: string) =>
    request<Order>(`/orders/${orderId}/pay`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ simulate_failure: simulateFailure }),
    }),

  refundStatus: (orderId: number, token: string) =>
    request<{ order_id: number; refund_status: string }>(
      `/orders/${orderId}/refund-status`,
      { headers: { Authorization: `Bearer ${token}` } },
    ),

  stockSocketUrl: (flashSaleId: number) =>
    `${WS_BASE}/ws/flash-sales/${flashSaleId}/stock`,
};
