import { mockApi } from "./mockApi";

export type ApiKeyRecord = {
  id: number;
  name: string;
  key_prefix: string;
  expires_at: string | null;
  last_used_at: string | null;
  can_view_devices: boolean;
  can_manage_keys: boolean;
  status: string;
  created_at: string;
};

export type AndroidDevice = {
  id: number;
  name: string;
  adb_serial: string;
  phone_ip: string | null;
  ssh_remote_port: number | null;
  model: string | null;
  notes: string | null;
  status: string;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AndroidDeviceStatus = {
  id: number | null;
  name: string;
  adb_serial: string;
  phone_ip: string | null;
  ssh_remote_port: number | null;
  model: string | null;
  online_status?: string;
  status: string;
  busy?: boolean;
  work_status?: string;
  detail: string;
  last_seen_at: string | null;
};

export type QueryRecord = {
  id: number;
  sku_id: string;
  status: string;
  tags: string[] | null;
  error_message: string | null;
  elapsed_ms: number | null;
  device_id: number | null;
  product_id: number | null;
  source_input: string | null;
  source_url: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type ProductRecord = {
  id: number;
  item_id: string;
  source_input: string | null;
  source_url: string | null;
  type: "manual" | "auto" | string;
  title: string | null;
  sales_volume: string | null;
  shop_id: string | null;
  shop_name: string | null;
  shop_url: string | null;
  shop_location: string | null;
  web_status: string;
  web_error: string | null;
  include_detail: boolean;
  detail_status: string;
  status: string;
  is_main: boolean;
  device_collected: boolean;
  original_price: string | null;
  deal_price: string | null;
  group_id: number | null;
  collected_at: string | null;
  latest_query?: QueryRecord | null;
  created_at: string;
  updated_at: string;
};

export type MetricSummary = {
  sku_id: string;
  product_id: number;
  title: string | null;
  original_price: string | null;
  deal_price: string | null;
  shop_name: string | null;
  sales_volume: string | null;
  product_created_at: string;
  product_updated_at: string;
  metrics: Record<string, number>;
  metric_updated_at: string | null;
};

export type MetricHistory = {
  sku_id: string;
  dim_key: string;
  dim_value: number;
  created_at: string;
};

export type MarketplaceItem = {
  item_id: string;
  title: string;
  price: string;
  tags?: string[];
};

export type MarketplaceStatus = {
  status: "idle" | "running" | "done" | "error";
  total: number;
  collected: number;
  items: MarketplaceItem[];
  error: string;
};

export type TagResult = {
  ok: boolean;
  sku_id: string;
  input?: string | null;
  source?: string | null;
  resolved_url?: string | null;
  tags: string[];
  items: Array<Record<string, unknown>>;
  elapsed_ms: number | null;
  error?: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE || "";
export const isMockApi = import.meta.env.VITE_MOCK_API === "true";

function headers(apiKey?: string): HeadersInit {
  return apiKey ? { "Content-Type": "application/json", "X-API-Key": apiKey } : { "Content-Type": "application/json" };
}

async function request<T>(path: string, init: RequestInit = {}, apiKey?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers(apiKey), ...(init.headers || {}) }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  }
  return data as T;
}

export type PageResult<T> = {
  items: T[];
  total: number;
};

const realApi = {
  getTags: (input: string, apiKey: string, deviceId?: number | null) => {
    const params = new URLSearchParams({ input });
    if (deviceId) params.set("deviceId", String(deviceId));
    return request<TagResult>(`/tags?${params.toString()}`, {}, apiKey);
  },
  listQueries: (apiKey: string) => request<QueryRecord[]>("/queries?limit=30", {}, apiKey),
  createQuery: (payload: { input?: string; product_id?: number | null; device_id?: number | null }, apiKey: string) =>
    request<QueryRecord>("/queries", { method: "POST", body: JSON.stringify(payload) }, apiKey),
  getQuery: (id: number, apiKey: string) => request<QueryRecord>(`/queries/${id}`, {}, apiKey),
  listProducts: (apiKey: string, params: { isMain?: boolean; page?: number; pageSize?: number; keyword?: string; type?: string; webStatus?: string; detailStatus?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.isMain !== undefined) qs.set("is_main", String(params.isMain));
    if (params.page) qs.set("page", String(params.page));
    if (params.pageSize) qs.set("page_size", String(params.pageSize));
    if (params.keyword) qs.set("keyword", params.keyword);
    if (params.type) qs.set("type", params.type);
    if (params.webStatus) qs.set("web_status", params.webStatus);
    if (params.detailStatus) qs.set("detail_status", params.detailStatus);
    return request<PageResult<ProductRecord>>(`/api/products?${qs.toString()}`, {}, apiKey);
  },
  getProduct: (id: number, apiKey: string) => request<ProductRecord>(`/api/products/${id}`, {}, apiKey),
  createProduct: (payload: { input: string; type?: string; title?: string | null; include_detail?: boolean; device_id?: number | null; is_main?: boolean; group_id?: number | null }, apiKey: string) =>
    request<ProductRecord>("/api/products", { method: "POST", body: JSON.stringify(payload) }, apiKey),
  refreshProduct: (id: number, apiKey: string) =>
    request<ProductRecord>(`/api/products/${id}/refresh`, { method: "POST" }, apiKey),
  updateProduct: (id: number, payload: { is_main?: boolean; group_id?: number | null }, apiKey: string) =>
    request<ProductRecord>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, apiKey),
  getProductGroup: (id: number, apiKey: string) =>
    request<ProductRecord[]>(`/api/products/${id}/group`, {}, apiKey),
  enqueueProductDetail: (id: number, apiKey: string) =>
    request<QueryRecord>(`/api/products/${id}/detail`, { method: "POST" }, apiKey),
  listDevices: (apiKey: string) => request<AndroidDevice[]>("/api/devices", {}, apiKey),
  metricSummary: (apiKey: string) => request<MetricSummary[]>("/api/tag-metrics/summary", {}, apiKey),
  metricHistory: (skuId: string, apiKey: string) => request<MetricHistory[]>(`/api/tag-metrics/history?sku_id=${encodeURIComponent(skuId)}`, {}, apiKey),
  deviceStatus: (apiKey: string) => request<{ serial: string; state: string; detail: string; raw: string }>("/api/devices/status", {}, apiKey),
  deviceStatuses: (apiKey: string) => request<{ devices: AndroidDeviceStatus[] }>("/api/devices/statuses", {}, apiKey),
  createDevice: (payload: Partial<AndroidDevice>, apiKey: string) =>
    request<AndroidDevice>("/api/devices", { method: "POST", body: JSON.stringify(payload) }, apiKey),
  listKeys: (apiKey: string) => request<ApiKeyRecord[]>("/api/keys", {}, apiKey),
  me: (apiKey: string) => request<ApiKeyRecord>("/me", {}, apiKey),
  createKey: (payload: { name: string; expires_at?: string | null; can_view_devices?: boolean; can_manage_keys?: boolean }, apiKey: string) =>
    request<{ id: number; name: string; key: string; key_prefix: string; expires_at: string | null; status: string }>(
      "/api/keys",
      { method: "POST", body: JSON.stringify(payload) },
      apiKey
    ),
  revokeKey: (id: number, apiKey: string) => request<{ ok: boolean }>(`/api/keys/${id}`, { method: "DELETE" }, apiKey),
  startMarketplaceCollect: (count: number, category: string, deviceId: number | null, apiKey: string) =>
    request<{ ok: boolean; count: number }>("/api/marketplace/collect", { method: "POST", body: JSON.stringify({ count, category, device_id: deviceId }) }, apiKey),
  marketplaceStatus: (apiKey: string) =>
    request<MarketplaceStatus>("/api/marketplace/status", {}, apiKey),
};

export const api = isMockApi ? mockApi : realApi;
