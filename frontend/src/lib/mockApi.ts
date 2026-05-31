import type {
  AndroidDevice,
  AndroidDeviceStatus,
  ApiKeyRecord,
  MarketplaceStatus,
  MetricHistory,
  MetricSummary,
  PageResult,
  ProductRecord,
  QueryRecord,
  TagResult,
} from "./api";

const now = new Date("2026-05-31T10:20:00+08:00").toISOString();

let nextProductId = 1006;
let nextKeyId = 4;
let nextDeviceId = 4;

const adminKey: ApiKeyRecord = {
  id: 1,
  name: "demo-admin",
  key_prefix: "demo-",
  expires_at: null,
  last_used_at: now,
  can_view_devices: true,
  can_manage_keys: true,
  status: "active",
  created_at: "2026-05-01T09:00:00+08:00",
};

const queries: QueryRecord[] = [
  {
    id: 501,
    sku_id: "xhs-demo-1001",
    status: "success",
    tags: ["通勤", "显瘦", "夏季", "高复购"],
    error_message: null,
    elapsed_ms: 1840,
    device_id: 1,
    product_id: 1001,
    source_input: "https://xhslink.com/demo/linen-shirt",
    source_url: "https://www.xiaohongshu.com/goods-detail/xhs-demo-1001",
    started_at: "2026-05-30T14:02:00+08:00",
    finished_at: "2026-05-30T14:02:02+08:00",
    created_at: "2026-05-30T14:01:58+08:00",
  },
  {
    id: 502,
    sku_id: "xhs-demo-1002",
    status: "success",
    tags: ["防晒", "轻薄", "户外", "收藏增长"],
    error_message: null,
    elapsed_ms: 2210,
    device_id: 1,
    product_id: 1002,
    source_input: "https://xhslink.com/demo/sun-jacket",
    source_url: "https://www.xiaohongshu.com/goods-detail/xhs-demo-1002",
    started_at: "2026-05-30T15:18:00+08:00",
    finished_at: "2026-05-30T15:18:02+08:00",
    created_at: "2026-05-30T15:17:55+08:00",
  },
];

const products: ProductRecord[] = [
  product(1001, "xhs-demo-1001", "法式亚麻短袖衬衫", "春棉实验室", "上海", "1.2万+", "129", "189", true, 101, queries[0]),
  product(1002, "xhs-demo-1002", "轻量防晒皮肤衣 UPF50+", "山野通勤", "杭州", "8600+", "169", "239", true, 102, queries[1]),
  product(1003, "xhs-demo-1003", "高腰直筒牛仔裤", "Daily Denim", "广州", "5400+", "199", "269", true, 103, null),
  product(1004, "xhs-demo-1004", "云感无钢圈内衣", "柔软事务所", "深圳", "7200+", "89", "129", false, 101, {
    ...queries[0],
    id: 503,
    sku_id: "xhs-demo-1004",
    product_id: 1004,
    tags: ["舒适", "无痕", "回购"],
  }),
  product(1005, "xhs-demo-1005", "冷萃咖啡随行杯", "晨间器物", "宁波", "3100+", "79", "99", true, 104, null),
];

let keys: ApiKeyRecord[] = [
  adminKey,
  { ...adminKey, id: 2, name: "operator", key_prefix: "op-demo-", can_manage_keys: false, created_at: "2026-05-18T11:00:00+08:00" },
  { ...adminKey, id: 3, name: "viewer", key_prefix: "view-demo-", can_view_devices: false, can_manage_keys: false, status: "revoked", created_at: "2026-05-20T16:30:00+08:00" },
];

let devices: AndroidDevice[] = [
  device(1, "vivo V2048A", "127.0.0.1:15555", "192.168.2.83", 15555, "PD2048", "主采集机"),
  device(2, "Redmi K70", "192.168.2.45:5555", "192.168.2.45", 5555, "23113RKC6C", "备用"),
  device(3, "Pixel 7", "emulator-5554", null, null, "Pixel 7", "离线测试机"),
];

let marketplaceStatus: MarketplaceStatus = {
  status: "done",
  total: 8,
  collected: 8,
  error: "",
  items: [
    { item_id: "xhs-market-01", title: "短款正肩 T 恤", price: "¥69 · 4200+", tags: ["基础款", "显瘦"] },
    { item_id: "xhs-market-02", title: "冰丝阔腿裤", price: "¥119 · 6800+", tags: ["凉感", "通勤"] },
    { item_id: "xhs-market-03", title: "复古棒球帽", price: "¥49 · 2600+", tags: ["配饰"] },
    { item_id: "xhs-market-04", title: "法式背心连衣裙", price: "¥159 · 3900+", tags: ["度假", "收腰"] },
  ],
};

function product(
  id: number,
  itemId: string,
  title: string,
  shop: string,
  location: string,
  sales: string,
  deal: string,
  original: string,
  isMain: boolean,
  groupId: number,
  latest: QueryRecord | null,
): ProductRecord {
  return {
    id,
    item_id: itemId,
    source_input: `https://xhslink.com/demo/${itemId}`,
    source_url: `https://www.xiaohongshu.com/goods-detail/${itemId}`,
    type: id % 2 ? "manual" : "auto",
    title,
    sales_volume: sales,
    shop_id: `shop-${id}`,
    shop_name: shop,
    shop_url: `https://www.xiaohongshu.com/vendor/${id}`,
    shop_location: location,
    web_status: "success",
    web_error: null,
    include_detail: Boolean(latest),
    detail_status: latest ? "success" : "none",
    status: "active",
    is_main: isMain,
    device_collected: Boolean(latest),
    original_price: original,
    deal_price: deal,
    group_id: groupId,
    collected_at: latest?.finished_at || null,
    latest_query: latest,
    created_at: "2026-05-28T09:30:00+08:00",
    updated_at: now,
  };
}

function device(id: number, name: string, adb: string, ip: string | null, port: number | null, model: string, notes: string): AndroidDevice {
  return {
    id,
    name,
    adb_serial: adb,
    phone_ip: ip,
    ssh_remote_port: port,
    model,
    notes,
    status: "active",
    last_seen_at: id === 3 ? null : now,
    created_at: "2026-05-10T10:00:00+08:00",
    updated_at: now,
  };
}

function statuses(): AndroidDeviceStatus[] {
  return [
    ...devices.map((item) => ({
      ...item,
      online_status: item.id === 3 ? "offline" : "device",
      busy: item.id === 2,
      work_status: item.id === 2 ? "collecting" : "idle",
      detail: item.id === 3 ? "device not found" : "adb connected",
    })),
    {
      id: null,
      name: "OPPO Find X7",
      adb_serial: "192.168.2.88:5555",
      phone_ip: "192.168.2.88",
      ssh_remote_port: 5555,
      model: "PHY110",
      online_status: "device",
      status: "device",
      busy: false,
      work_status: "idle",
      detail: "detected but not saved",
      last_seen_at: now,
    },
  ];
}

function wait<T>(value: T): Promise<T> {
  return new Promise((resolve) => window.setTimeout(() => resolve(value), 180));
}

function nextQuery(productId: number, skuId: string): QueryRecord {
  return {
    id: Math.max(...queries.map((q) => q.id), 500) + 1,
    sku_id: skuId,
    status: "success",
    tags: ["新品", "种草", "价格友好"],
    error_message: null,
    elapsed_ms: 960,
    device_id: 1,
    product_id: productId,
    source_input: skuId,
    source_url: `https://www.xiaohongshu.com/goods-detail/${skuId}`,
    started_at: now,
    finished_at: now,
    created_at: now,
  };
}

function summaryFromProduct(item: ProductRecord): MetricSummary {
  const seed = item.id % 10;
  return {
    sku_id: item.item_id,
    product_id: item.id,
    title: item.title,
    original_price: item.original_price,
    deal_price: item.deal_price,
    shop_name: item.shop_name,
    sales_volume: item.sales_volume,
    product_created_at: item.created_at,
    product_updated_at: item.updated_at,
    metrics: {
      "24h_cart": 80 + seed * 37,
      "7d_fav": 220 + seed * 64,
    },
    metric_updated_at: now,
  };
}

export const mockApi = {
  getTags: (input: string): Promise<TagResult> =>
    wait({
      ok: true,
      sku_id: input || "xhs-demo-1001",
      input,
      source: "mock",
      resolved_url: "https://www.xiaohongshu.com/goods-detail/xhs-demo-1001",
      tags: ["通勤", "显瘦", "夏季"],
      items: [],
      elapsed_ms: 128,
    }),
  listQueries: (): Promise<QueryRecord[]> => wait([...queries]),
  createQuery: (payload: { input?: string; product_id?: number | null }): Promise<QueryRecord> => {
    const target = products.find((item) => item.id === payload.product_id) || products[0];
    const query = nextQuery(target.id, target.item_id);
    queries.unshift(query);
    target.latest_query = query;
    target.detail_status = "success";
    target.device_collected = true;
    return wait(query);
  },
  getQuery: (id: number): Promise<QueryRecord> => wait(queries.find((query) => query.id === id) || queries[0]),
  listProducts: (_apiKey: string, params: { isMain?: boolean; page?: number; pageSize?: number; keyword?: string; type?: string; webStatus?: string; detailStatus?: string } = {}): Promise<PageResult<ProductRecord>> => {
    const keyword = (params.keyword || "").trim().toLowerCase();
    let items = products.filter((item) => params.isMain === undefined || item.is_main === params.isMain);
    if (keyword) items = items.filter((item) => [item.title, item.shop_name, item.item_id].join(" ").toLowerCase().includes(keyword));
    if (params.type) items = items.filter((item) => item.type === params.type);
    if (params.webStatus) items = items.filter((item) => item.web_status === params.webStatus);
    if (params.detailStatus) items = items.filter((item) => item.detail_status === params.detailStatus);
    const page = params.page || 1;
    const pageSize = params.pageSize || 10;
    return wait({ items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length });
  },
  getProduct: (id: number): Promise<ProductRecord> => wait(products.find((item) => item.id === id) || products[0]),
  createProduct: (payload: { input: string; type?: string; include_detail?: boolean; is_main?: boolean; group_id?: number | null }): Promise<ProductRecord> => {
    const id = nextProductId++;
    const query = payload.include_detail ? nextQuery(id, `xhs-demo-${id}`) : null;
    if (query) queries.unshift(query);
    const item = product(id, `xhs-demo-${id}`, `演示商品 ${id}`, "Demo Studio", "上海", "1200+", "99", "139", payload.is_main ?? true, payload.group_id || id, query);
    item.source_input = payload.input;
    item.type = payload.type || "manual";
    products.unshift(item);
    return wait(item);
  },
  refreshProduct: (id: number): Promise<ProductRecord> => {
    const item = products.find((product) => product.id === id) || products[0];
    item.updated_at = new Date().toISOString();
    return wait(item);
  },
  updateProduct: (id: number, payload: { is_main?: boolean; group_id?: number | null }): Promise<ProductRecord> => {
    const item = products.find((product) => product.id === id) || products[0];
    if (payload.is_main !== undefined) item.is_main = payload.is_main;
    if (payload.group_id !== undefined) item.group_id = payload.group_id;
    return wait(item);
  },
  getProductGroup: (id: number): Promise<ProductRecord[]> => {
    const item = products.find((product) => product.id === id);
    return wait(products.filter((product) => product.group_id && product.group_id === item?.group_id));
  },
  enqueueProductDetail: (id: number): Promise<QueryRecord> => {
    const item = products.find((product) => product.id === id) || products[0];
    const query = nextQuery(item.id, item.item_id);
    queries.unshift(query);
    item.latest_query = query;
    item.detail_status = "success";
    item.device_collected = true;
    return wait(query);
  },
  listDevices: (): Promise<AndroidDevice[]> => wait([...devices]),
  metricSummary: (): Promise<MetricSummary[]> => wait(products.map(summaryFromProduct)),
  metricHistory: (skuId: string): Promise<MetricHistory[]> => {
    const dates = ["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29", "2026-05-30"];
    return wait(dates.flatMap((date, index) => [
      { sku_id: skuId, dim_key: "24h_cart", dim_value: 80 + index * 24, created_at: `${date}T10:00:00+08:00` },
      { sku_id: skuId, dim_key: "7d_fav", dim_value: 220 + index * 41, created_at: `${date}T10:00:00+08:00` },
    ]));
  },
  deviceStatus: (): Promise<{ serial: string; state: string; detail: string; raw: string }> =>
    wait({ serial: "127.0.0.1:15555", state: "device", detail: "mock connected", raw: "List of devices attached" }),
  deviceStatuses: (): Promise<{ devices: AndroidDeviceStatus[] }> => wait({ devices: statuses() }),
  createDevice: (payload: Partial<AndroidDevice>): Promise<AndroidDevice> => {
    const item = device(nextDeviceId++, payload.name || "Demo Device", payload.adb_serial || "demo-serial", payload.phone_ip || null, payload.ssh_remote_port || null, payload.model || "Demo", payload.notes || "");
    devices.unshift(item);
    return wait(item);
  },
  listKeys: (): Promise<ApiKeyRecord[]> => wait([...keys]),
  me: (): Promise<ApiKeyRecord> => wait(adminKey),
  createKey: (payload: { name: string; expires_at?: string | null; can_view_devices?: boolean; can_manage_keys?: boolean }): Promise<{ id: number; name: string; key: string; key_prefix: string; expires_at: string | null; status: string }> => {
    const id = nextKeyId++;
    const key = `demo-key-${id}-${Math.random().toString(36).slice(2, 10)}`;
    keys.unshift({
      id,
      name: payload.name,
      key_prefix: key.slice(0, 9),
      expires_at: payload.expires_at || null,
      last_used_at: null,
      can_view_devices: !!payload.can_view_devices,
      can_manage_keys: !!payload.can_manage_keys,
      status: "active",
      created_at: new Date().toISOString(),
    });
    return wait({ id, name: payload.name, key, key_prefix: key.slice(0, 9), expires_at: payload.expires_at || null, status: "active" });
  },
  revokeKey: (id: number): Promise<{ ok: boolean }> => {
    keys = keys.map((key) => key.id === id ? { ...key, status: "revoked" } : key);
    return wait({ ok: true });
  },
  startMarketplaceCollect: (count: number, category: string): Promise<{ ok: boolean; count: number }> => {
    marketplaceStatus = {
      status: "done",
      total: count,
      collected: count,
      error: "",
      items: Array.from({ length: Math.min(count, 12) }, (_, index) => ({
        item_id: `xhs-${category}-${String(index + 1).padStart(2, "0")}`,
        title: `${category} 市集商品 ${index + 1}`,
        price: `¥${59 + index * 12} · ${1200 + index * 430}+`,
        tags: index % 2 ? ["高转化", "趋势"] : ["低价", "新品"],
      })),
    };
    return wait({ ok: true, count });
  },
  marketplaceStatus: (): Promise<MarketplaceStatus> => wait(marketplaceStatus),
};
