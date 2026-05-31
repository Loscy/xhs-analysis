import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  ConfigProvider,
  Empty,
  Form,
  Input,
  InputNumber,
  Layout,
  List,
  Menu,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  theme,
} from "antd";
import {
  ApiOutlined,
  KeyOutlined,
  LoginOutlined,
  LogoutOutlined,
  MobileOutlined,
  PlusOutlined,
  ReloadOutlined,
  ShoppingOutlined,
} from "@ant-design/icons";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import "antd/dist/reset.css";
import { AndroidDevice, AndroidDeviceStatus, ApiKeyRecord, MarketplaceItem, MarketplaceStatus, MetricHistory, MetricSummary, ProductRecord, QueryRecord, api } from "./lib/api";
import "./styles/app.css";

const { Header, Sider, Content } = Layout;
const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const API_KEY_STORAGE_KEY = "xhs_api_key";

type DeviceFormValue = {
  name: string;
  adb_serial: string;
  phone_ip?: string;
  ssh_remote_port?: string;
  model?: string;
};
type KeyFormValue = {
  name: string;
  days: string;
  can_view_devices?: boolean;
  can_manage_keys?: boolean;
};
type ProductFilters = {
  keyword: string;
  type?: string;
  webStatus?: string;
  detailStatus?: string;
};
type DeviceFilters = {
  keyword: string;
  online?: string;
  work?: string;
};
type KeyFilters = {
  keyword: string;
  status?: string;
  permission?: string;
};

const TAG_DIMENSIONS = [
  { key: "24h_cart", label: "24小时内加购" },
  { key: "7d_fav", label: "近7天新增收藏" },
];

function getStoredApiKey() {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || "";
}

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          colorInfo: "#06b6d4",
          borderRadius: 8,
          fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        components: {
          Layout: { siderBg: "#07111f", triggerBg: "#07111f" },
          Menu: { darkItemBg: "#07111f", darkItemSelectedBg: "#11345a" },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <RootRoutes />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

function RootRoutes() {
  const [apiKey, setApiKey] = useState(getStoredApiKey);
  const [currentKey, setCurrentKey] = useState<ApiKeyRecord | null>(null);
  const [checking, setChecking] = useState(Boolean(getStoredApiKey()));
  const navigate = useNavigate();
  const location = useLocation();

  async function unlock(value: string) {
    localStorage.setItem(API_KEY_STORAGE_KEY, value);
    setApiKey(value);
    const key = await api.me(value);
    setCurrentKey(key);
    const target = location.pathname === "/" || location.pathname === "/login" || location.pathname === "/query" ? "/products/main" : location.pathname;
    navigate(target, { replace: true });
  }

  function logout() {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    setApiKey("");
    setCurrentKey(null);
    navigate("/login", { replace: true });
  }

  useEffect(() => {
    if (!apiKey) return;
    setChecking(true);
    api.me(apiKey)
      .then(setCurrentKey)
      .catch(logout)
      .finally(() => setChecking(false));
  }, [apiKey]);

  return (
    <Routes>
      <Route path="/login" element={<KeyGate onUnlock={unlock} />} />
      <Route path="/" element={apiKey ? <Navigate to="/products/main" replace /> : <Navigate to="/login" replace />} />
      <Route
        path="/*"
        element={
          apiKey ? (
            checking || !currentKey ? <LoadingGate /> : <ConsoleShell apiKey={apiKey} currentKey={currentKey} logout={logout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

function LoadingGate() {
  return (
    <main className="gate loadingGate">
      <Card className="gateCard" variant="borderless">
        <Space direction="vertical" size={18}>
          <div className="brandMark">X</div>
          <Title level={3}>正在进入平台</Title>
          <Text type="secondary">请稍候</Text>
        </Space>
      </Card>
    </main>
  );
}

function KeyGate({ onUnlock }: { onUnlock: (apiKey: string) => Promise<void> }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const key = value.trim();
    if (!key) return;
    setLoading(true);
    setError("");
    try {
      await api.me(key);
      onUnlock(key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "密钥无效或已过期");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="gate">
      <Card className="gateCard" variant="borderless">
        <Space direction="vertical" size={34} className="fullWidth">
          <Space size={12}>
            <div className="brandMark">X</div>
            <Text strong className="brandText">小红书数据平台</Text>
          </Space>
          <div>
            <Title level={1}>小红书数据平台</Title>
            <Paragraph type="secondary">输入访问凭证，进入商品数据工作台。</Paragraph>
          </div>
          <form onSubmit={submit}>
            <Space direction="vertical" size={12} className="fullWidth">
              <Input.Password size="large" value={value} onChange={(e) => setValue(e.target.value)} placeholder="访问凭证" autoFocus />
              {error && <Alert type="error" showIcon message={error} />}
              <Button size="large" type="primary" htmlType="submit" block loading={loading} disabled={!value.trim()} icon={<LoginOutlined />}>
                进入平台
              </Button>
            </Space>
          </form>
        </Space>
      </Card>
      <Card className="gatePreview" variant="borderless">
        <Space direction="vertical" size={20} className="fullWidth">
          <Space><ApiOutlined /><Text>商品数据洞察</Text></Space>
          <Row gutter={[12, 12]}>
            <Col span={8}><Statistic title="商品" value="追踪" /></Col>
            <Col span={8}><Statistic title="销量" value="分析" /></Col>
            <Col span={8}><Statistic title="店铺" value="画像" /></Col>
          </Row>
        </Space>
      </Card>
    </main>
  );
}

function ConsoleShell({
  apiKey,
  currentKey,
  logout,
}: {
  apiKey: string;
  currentKey: ApiKeyRecord | null;
  logout: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const tab = pathToTab(location.pathname);

  return (
    <Layout className="appLayout">
      <Sider width={272} className="sidebar" breakpoint="lg" collapsedWidth={0}>
        <Space direction="vertical" size={20} className="fullWidth">
          <Space size={12} className="brand">
            <div className="brandMark">X</div>
            <div>
              <Title level={4}>小红书数据平台</Title>
              <Text type="secondary">博主选品工作台</Text>
            </div>
          </Space>
          <Card size="small" className="sessionCard">
            <Space>
              <KeyOutlined />
              <div>
                <Text strong>{apiKey.slice(0, 9)}...</Text>
                <br />
                <Text type="secondary">已解锁控制台</Text>
              </div>
            </Space>
            <Button size="small" type="text" icon={<LogoutOutlined />} onClick={logout} />
          </Card>
          <Menu
            theme="dark"
            mode="inline"
            defaultOpenKeys={["grp-products"]}
            selectedKeys={[tab]}
            onClick={(item) => navigate(`/${item.key}`)}
            items={[
              {
                key: "grp-products",
                icon: <ShoppingOutlined />,
                label: "商品",
                children: [
                  { key: "products/main", label: "主商品" },
                  { key: "products/all", label: "全部商品" },
                  { key: "products/marketplace", label: "市集采集" },
                  { key: "products/analysis", label: "标签分析" },
                ],
              },
              currentKey?.can_view_devices ? { key: "devices", icon: <MobileOutlined />, label: "设备" } : null,
              currentKey?.can_manage_keys ? { key: "keys", icon: <KeyOutlined />, label: "密钥" } : null,
            ].filter(Boolean)}
          />
        </Space>
      </Sider>
      <Layout>
        <Header className="mobileHeader">
          <Space>
            <div className="brandMark small">X</div>
            <Text strong>小红书数据平台</Text>
          </Space>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout} />
        </Header>
        <Content className="content">
          <Routes>
            <Route path="/products/main" element={<ProductsPage apiKey={apiKey} isMain={true} />} />
            <Route path="/products/all" element={<ProductsPage apiKey={apiKey} />} />
            <Route path="/products/marketplace" element={<MarketplacePage apiKey={apiKey} />} />
            <Route path="/products/analysis" element={<TagAnalysisPage apiKey={apiKey} />} />
            <Route path="/products" element={<Navigate to="/products/main" replace />} />
            <Route path="/query" element={<Navigate to="/products/main" replace />} />
            <Route path="/devices" element={currentKey?.can_view_devices ? <DevicesPage apiKey={apiKey} /> : <Navigate to="/products/main" replace />} />
            <Route path="/keys" element={currentKey?.can_manage_keys ? <KeysPage apiKey={apiKey} /> : <Navigate to="/products/main" replace />} />
            <Route path="*" element={<Navigate to="/products/main" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

function pathToTab(pathname: string): string {
  if (pathname.startsWith("/devices")) return "devices";
  if (pathname.startsWith("/keys")) return "keys";
  if (pathname === "/products/all") return "products/all";
  if (pathname === "/products/marketplace") return "products/marketplace";
  if (pathname === "/products/analysis") return "products/analysis";
  return "products/main";
}

function tabToPath(key: string) {
  return `/${key}`;
}

function statusLabel(value?: string | null) {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "进行中",
    success: "已完成",
    failed: "失败",
    none: "未补充",
    active: "可用",
    revoked: "停用",
  };
  return value ? labels[value] || value : "-";
}

function ProductsPage({ apiKey, isMain }: { apiKey: string; isMain?: boolean }) {
  const [goodsInput, setGoodsInput] = useState("https://xhslink.com/m/314GLxjHAms");
  const [includeDetail, setIncludeDetail] = useState(false);
  const [products, setProducts] = useState<ProductRecord[]>([]);
  const [devices, setDevices] = useState<AndroidDeviceStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<ProductRecord | null>(null);
  const [groupProducts, setGroupProducts] = useState<ProductRecord[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [deviceId, setDeviceId] = useState<number | null>(null);
  const [formIsMain, setFormIsMain] = useState(true);
  const [formGroupId, setFormGroupId] = useState<number | null>(null);
  const [filters, setFilters] = useState<ProductFilters>({ keyword: "" });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const selectableDevices = useMemo(() => devices.filter((device) => device.id), [devices]);
  const idleDeviceCount = useMemo(
    () => devices.filter((device) => device.id && (device.online_status || device.status) === "device" && !device.busy).length,
    [devices],
  );

  async function refresh(p?: number, ps?: number) {
    const pPage = p ?? page;
    const pSize = ps ?? pageSize;
    const [productData, statusData] = await Promise.all([
      api.listProducts(apiKey, {
        isMain,
        page: pPage,
        pageSize: pSize,
        keyword: filters.keyword || undefined,
        type: filters.type,
        webStatus: filters.webStatus,
        detailStatus: filters.detailStatus,
      }).catch(() => ({ items: [], total: 0 })),
      api.deviceStatuses(apiKey).catch(() => ({ devices: [] })),
    ]);
    setProducts(productData.items || []);
    setTotal(productData.total || 0);
    const nextDevices = Array.isArray(statusData.devices) ? statusData.devices : [];
    setDevices(nextDevices);
    if (!deviceId) {
      const firstOnline = nextDevices.find((device) => device.id && (device.online_status || device.status) === "device" && !device.busy);
      setDeviceId(firstOnline?.id ?? null);
    }
  }

  async function openGroup(product: ProductRecord) {
    setSelectedGroup(product);
    if (product.group_id) {
      const group = await api.getProductGroup(product.id, apiKey).catch(() => []);
      setGroupProducts(Array.isArray(group) ? group : []);
    } else {
      setGroupProducts([product]);
    }
  }

  async function toggleIsMain(product: ProductRecord, value: boolean) {
    await api.updateProduct(product.id, { is_main: value }, apiKey);
    await refresh();
  }

  function onFilterChange(next: ProductFilters) {
    setFilters(next);
    setPage(1);
  }

  async function submit() {
    setLoading(true);
    setError("");
    try {
      const product = await api.createProduct({
        input: goodsInput.trim(),
        type: "manual",
        include_detail: includeDetail,
        device_id: includeDetail ? deviceId : null,
        is_main: formIsMain,
        group_id: formGroupId,
      }, apiKey);
      setCreateOpen(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh(page, pageSize).catch(() => undefined);
  }, [apiKey, isMain, page, pageSize, filters]);

  return (
    <>
      <Card
        title="选品库"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refresh()} />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { setFormIsMain(true); setFormGroupId(null); setCreateOpen(true); }}>新增商品</Button>
          </Space>
        }
      >
          <Space direction="vertical" size={14} className="fullWidth">
            <Text type="secondary">{isMain ? "展示主商品列表，点击关联规格查看同组商品。" : "展示全部商品，可编辑是否为主商品。"}</Text>
            <Row gutter={[10, 10]}>
              <Col xs={24} md={9}>
                <Input allowClear placeholder="搜索商品、店铺" value={filters.keyword} onChange={(e) => onFilterChange({ ...filters, keyword: e.target.value })} />
              </Col>
              <Col xs={12} md={5}>
                <Select
                  allowClear
                  className="fullWidth"
                  placeholder="类型"
                  value={filters.type}
                  onChange={(value) => onFilterChange({ ...filters, type: value })}
                  options={[
                    { value: "manual", label: "手动" },
                    { value: "auto", label: "自动" },
                  ]}
                />
              </Col>
              <Col xs={12} md={5}>
                <Select
                  allowClear
                  className="fullWidth"
                  placeholder="基础信息"
                  value={filters.webStatus}
                  onChange={(value) => onFilterChange({ ...filters, webStatus: value })}
                  options={["pending", "running", "success", "failed"].map((value) => ({ value, label: value }))}
                />
              </Col>
              <Col xs={12} md={5}>
                <Select
                  allowClear
                  className="fullWidth"
                  placeholder="页面标签"
                  value={filters.detailStatus}
                  onChange={(value) => onFilterChange({ ...filters, detailStatus: value })}
                  options={[
                    { value: "none", label: "未补充" },
                    { value: "pending", label: "等待中" },
                    { value: "running", label: "进行中" },
                    { value: "success", label: "已补充" },
                    { value: "failed", label: "失败" },
                  ]}
                />
              </Col>
            </Row>
            <Table
              rowKey="id"
              dataSource={products}
              pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
              onChange={(pag) => { setPage(pag.current || 1); setPageSize(pag.pageSize || 10); }}
              scroll={{ x: 980 }}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无商品" /> }}
              columns={[
                {
                  title: "商品",
                  dataIndex: "title",
                  render: (_: unknown, product: ProductRecord) => (
                    <Space direction="vertical" size={0}>
                      <a href={`https://www.xiaohongshu.com/goods-detail/${product.item_id}`} target="_blank" rel="noreferrer">{product.title || product.item_id}</a>
                    </Space>
                  ),
                },
                {
                  title: "销量",
                  dataIndex: "sales_volume",
                  width: 110,
                  sorter: (a: ProductRecord, b: ProductRecord) => {
                    const parseNum = (s: string | null) => { const m = (s || "").match(/(\d+)/); return m ? parseInt(m[1]) : 0; };
                    return parseNum(a.sales_volume) - parseNum(b.sales_volume);
                  },
                  render: (_: unknown, product: ProductRecord) => product.sales_volume || "-",
                },
                {
                  title: "到手价",
                  dataIndex: "deal_price",
                  width: 110,
                  sorter: (a: ProductRecord, b: ProductRecord) => (parseFloat(a.deal_price || "0") || 0) - (parseFloat(b.deal_price || "0") || 0),
                  render: (_: unknown, product: ProductRecord) => product.deal_price ? <Text strong>¥{product.deal_price}</Text> : "-",
                },
                {
                  title: "原价",
                  dataIndex: "original_price",
                  width: 110,
                  sorter: (a: ProductRecord, b: ProductRecord) => (parseFloat(a.original_price || "0") || 0) - (parseFloat(b.original_price || "0") || 0),
                  render: (_: unknown, product: ProductRecord) => product.original_price ? <Text delete type="secondary">¥{product.original_price}</Text> : "-",
                },
                {
                  title: "店铺名称",
                  dataIndex: "shop_name",
                  width: 190,
                  render: (_: unknown, product: ProductRecord) => (
                    <Space direction="vertical" size={0}>
                      {product.shop_name ? (
                        product.shop_url ? <a href={product.shop_url} target="_blank" rel="noreferrer">{product.shop_name}</a> : <Text>{product.shop_name}</Text>
                      ) : "-"}
                      {product.shop_location && <Text type="secondary">{product.shop_location}</Text>}
                    </Space>
                  ),
                },
                {
                  title: "标签",
                  dataIndex: "latest_query",
                  render: (_: unknown, product: ProductRecord) => (
                    <Space wrap>
                      {(product.latest_query?.tags || []).map((tag) => <Tag color="cyan" key={tag}>{tag}</Tag>)}
                      {!product.latest_query?.tags?.length ? <Text type="secondary">-</Text> : null}
                    </Space>
                  ),
                },
                {
                  title: "基础信息",
                  width: 110,
                  render: (_: unknown, product: ProductRecord) => (
                    <Tag color={product.web_status === "success" ? "success" : product.web_status === "failed" ? "error" : "processing"}>{statusLabel(product.web_status)}</Tag>
                  ),
                },
                ...(!isMain ? [{
                  title: "主商品",
                  width: 90,
                  render: (_: unknown, product: ProductRecord) => (
                    <Checkbox checked={product.is_main} onChange={(e) => toggleIsMain(product, e.target.checked)} />
                  ),
                }] : []),
                {
                  title: "操作",
                  width: 250,
                  fixed: "right",
                  render: (_: unknown, product: ProductRecord) => (
                    <Space>
                      <Button size="small" onClick={() => api.refreshProduct(product.id, apiKey).then(() => refresh())}>刷新</Button>
                      {!product.device_collected && (
                        <Button size="small" disabled={product.detail_status === "pending" || product.detail_status === "running"} onClick={() => api.enqueueProductDetail(product.id, apiKey).then(() => refresh())}>
                          {product.detail_status === "pending" || product.detail_status === "running" ? "补全中" : "设备补全"}
                        </Button>
                      )}
                      <Button size="small" type="primary" onClick={() => openGroup(product)}>规格</Button>
                    </Space>
                  ),
                },
              ]}
            />
          </Space>
      </Card>
      <Modal
        title="新增选品"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
          <Space direction="vertical" size={14} className="fullWidth">
            <Text type="secondary">粘贴小红书分享文案、商品链接或商品编号。</Text>
            <Alert type="info" showIcon message={`当前可用补充设备 ${idleDeviceCount} 台。未勾选补充页面标签时不会使用设备。`} />
            <Form layout="vertical" onFinish={submit}>
              <Form.Item label="商品信息">
                <TextArea rows={5} value={goodsInput} onChange={(e) => setGoodsInput(e.target.value)} placeholder="粘贴分享文案或短链" />
              </Form.Item>
              <Form.Item>
                <Checkbox checked={includeDetail} onChange={(e) => setIncludeDetail(e.target.checked)}>
                  手机设备获取页面标签
                </Checkbox>
              </Form.Item>
              {includeDetail && (
                <Form.Item label="补充设备">
                  <Select
                    value={deviceId ?? undefined}
                    placeholder="自动选择在线且闲置设备"
                    allowClear
                    onChange={(value) => setDeviceId(value ?? null)}
                    options={selectableDevices.map((device) => ({
                      value: device.id,
                      label: `${device.name} · ${device.adb_serial} · ${device.online_status || device.status} · ${device.work_status || "idle"}`,
                      disabled: (device.online_status || device.status) !== "device" || device.busy,
                    }))}
                  />
                </Form.Item>
              )}
              <Button type="primary" htmlType="submit" loading={loading} disabled={!goodsInput.trim()} icon={<PlusOutlined />}>
                新增选品
              </Button>
            </Form>
            {error && <Alert type="error" message={error} showIcon />}
          </Space>
      </Modal>
      <Modal
        title={`关联规格 — ${selectedGroup?.title || selectedGroup?.item_id || ""}`}
        open={!!selectedGroup}
        onCancel={() => { setSelectedGroup(null); setGroupProducts([]); }}
        footer={null}
        width={920}
      >
        {selectedGroup && <ProductDetail products={groupProducts} />}
      </Modal>
    </>
  );
}

function ProductDetail({ products }: { products: ProductRecord[] }) {
  return (
      <Space direction="vertical" size={14} className="fullWidth">
        <Text type="secondary">共 {products.length} 个关联商品</Text>
        <Table
          size="small"
          rowKey="id"
          dataSource={products}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 860 }}
          columns={[
            {
              title: "商品",
              render: (_: unknown, product: ProductRecord) => (
                <a href={`https://www.xiaohongshu.com/goods-detail/${product.item_id}`} target="_blank" rel="noreferrer">{product.title || product.item_id}</a>
              ),
            },
            { title: "销量", dataIndex: "sales_volume", width: 110, render: (v) => v || "-" },
            { title: "到手价", dataIndex: "deal_price", width: 100, render: (v) => v ? <Text strong>¥{v}</Text> : "-" },
            { title: "原价", dataIndex: "original_price", width: 100, render: (v) => v ? <Text delete type="secondary">¥{v}</Text> : "-" },
            {
              title: "店铺",
              render: (_: unknown, product: ProductRecord) => (
                <Space direction="vertical" size={0}>
                  {product.shop_name || "-"}
                  {product.shop_location && <Text type="secondary">{product.shop_location}</Text>}
                </Space>
              ),
            },
            {
              title: "标签",
              render: (_: unknown, product: ProductRecord) => (
                <Space wrap>
                  {(product.latest_query?.tags || []).map((tag) => <Tag color="green" key={tag}>{tag}</Tag>)}
                  {!product.latest_query?.tags?.length ? <Text type="secondary">暂无</Text> : null}
                </Space>
              ),
            },
            {
              title: "主商品",
              width: 80,
              render: (_: unknown, product: ProductRecord) => product.is_main ? <Tag color="blue">主</Tag> : <Tag>子</Tag>,
            },
          ]}
        />
      </Space>
  );
}

function MarketplacePage({ apiKey }: { apiKey: string }) {
  const [count, setCount] = useState(10);
  const [category, setCategory] = useState("T恤");
  const [deviceId, setDeviceId] = useState<number | null>(null);
  const [devices, setDevices] = useState<AndroidDeviceStatus[]>([]);
  const [status, setStatus] = useState<MarketplaceStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const selectableDevices = useMemo(() => devices.filter((d) => d.id), [devices]);

  async function fetchStatus() {
    const data = await api.marketplaceStatus(apiKey).catch(() => ({
      status: "idle" as const, total: 0, collected: 0, items: [], error: "",
    }));
    setStatus(data);
    return data;
  }

  async function loadDevices() {
    const statusData = await api.deviceStatuses(apiKey).catch(() => ({ devices: [] }));
    const nextDevices = Array.isArray(statusData.devices) ? statusData.devices : [];
    setDevices(nextDevices);
    if (!deviceId) {
      const firstOnline = nextDevices.find((d) => d.id && (d.online_status || d.status) === "device" && !d.busy);
      setDeviceId(firstOnline?.id ?? null);
    }
  }

  async function startCollect() {
    setLoading(true);
    setError("");
    try {
      await api.startMarketplaceCollect(count, category, deviceId, apiKey);
      startPolling();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function startPolling() {
    stopPolling();
    pollRef.current = setInterval(async () => {
      const data = await fetchStatus();
      if (data.status !== "running") stopPolling();
    }, 2000);
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    fetchStatus().then((data) => {
      if (data.status === "running") startPolling();
    });
    loadDevices();
    return stopPolling;
  }, [apiKey]);

  const isRunning = status?.status === "running";

  return (
    <Card
      title="市集采集"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchStatus(); loadDevices(); }} />
          <Button
            type="primary"
            loading={loading}
            disabled={isRunning}
            onClick={startCollect}
          >
            {isRunning ? "采集中..." : "开始采集"}
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" size={14} className="fullWidth">
        <Text type="secondary">自动打开小红书市集并按分类批量采集商品到选品库。</Text>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Space>
              <Text>分类</Text>
              <Select
                value={category}
                onChange={setCategory}
                disabled={isRunning}
                style={{ width: 120 }}
                options={[{ value: "T恤", label: "穿搭 / T恤" }]}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Text>数量</Text>
              <InputNumber
                min={1}
                max={30}
                value={count}
                onChange={(v) => setCount(v ?? 10)}
                disabled={isRunning}
                style={{ width: 80 }}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Text>设备</Text>
              <Select
                value={deviceId ?? undefined}
                placeholder="自动选择"
                allowClear
                disabled={isRunning}
                style={{ width: 240 }}
                onChange={(value) => setDeviceId(value ?? null)}
                options={selectableDevices.map((d) => ({
                  value: d.id,
                  label: `${d.name} · ${(d.online_status || d.status) === "device" ? "在线" : "离线"} · ${d.busy ? "占用" : "闲置"}`,
                  disabled: (d.online_status || d.status) !== "device" || d.busy,
                }))}
              />
            </Space>
          </Col>
        </Row>
        {status && status.status !== "idle" && (
          <>
            {isRunning && (
              <Alert
                type="info"
                showIcon
                message={`正在采集 ${status.collected}/${status.total}...`}
              />
            )}
            {status.status === "done" && (
              <Alert
                type="success"
                showIcon
                message={`采集完成，共 ${status.collected} 个商品`}
              />
            )}
            {status.status === "error" && (
              <Alert type="error" showIcon message={status.error} />
            )}
          </>
        )}
        {status && status.items.length > 0 && (
          <Table
            size="small"
            rowKey="item_id"
            dataSource={status.items}
            pagination={{ pageSize: 10 }}
            scroll={{ x: 600 }}
            columns={[
              {
                title: "#",
                width: 50,
                render: (_: unknown, __: MarketplaceItem, i: number) => i + 1,
              },
              {
                title: "商品ID",
                dataIndex: "item_id",
                render: (id: string) => (
                  <a href={`https://www.xiaohongshu.com/goods-detail/${id}`} target="_blank" rel="noreferrer">{id}</a>
                ),
              },
              {
                title: "标题",
                dataIndex: "title",
                render: (v: string) => v || "-",
              },
              {
                title: "价格/销量",
                dataIndex: "price",
                render: (v: string) => v || "-",
              },
              {
                title: "标签",
                render: (_: unknown, item: MarketplaceItem) => (
                  <Space wrap>
                    {(item.tags || []).map((tag) => <Tag color="cyan" key={tag}>{tag}</Tag>)}
                    {!item.tags?.length && <Text type="secondary">-</Text>}
                  </Space>
                ),
              },
            ]}
          />
        )}
        {error && <Alert type="error" message={error} showIcon />}
      </Space>
    </Card>
  );
}

function TagAnalysisPage({ apiKey }: { apiKey: string }) {
  const [summaries, setSummaries] = useState<MetricSummary[]>([]);
  const [selectedDims, setSelectedDims] = useState<string[]>([]);
  const [chartSkuId, setChartSkuId] = useState<string | null>(null);
  const [history, setHistory] = useState<MetricHistory[]>([]);

  async function refresh() {
    const data = await api.metricSummary(apiKey).catch(() => []);
    setSummaries(Array.isArray(data) ? data : []);
  }

  async function openChart(skuId: string) {
    setChartSkuId(skuId);
    const data = await api.metricHistory(skuId, apiKey).catch(() => []);
    setHistory(Array.isArray(data) ? data : []);
  }

  useEffect(() => { refresh().catch(() => undefined); }, [apiKey]);

  const filtered = useMemo(() =>
    selectedDims.length ? summaries.filter((s) => selectedDims.some((k) => s.metrics[k] !== undefined)) : summaries,
    [summaries, selectedDims],
  );

  const dimColumns = selectedDims.map((dimKey) => {
    const dim = TAG_DIMENSIONS.find((d) => d.key === dimKey)!;
    return {
      title: dim.label,
      dataIndex: dimKey,
      width: 160,
      sorter: (a: MetricSummary, b: MetricSummary) => (a.metrics[dimKey] ?? 0) - (b.metrics[dimKey] ?? 0),
      render: (_: unknown, row: MetricSummary) => {
        const val = row.metrics[dimKey];
        return val !== undefined
          ? <a onClick={() => openChart(row.sku_id)} style={{ cursor: "pointer", fontWeight: 600 }}>{val}</a>
          : "-";
      },
    };
  });

  return (
    <>
      <Card title="标签分析" extra={<Button icon={<ReloadOutlined />} onClick={refresh} />}>
        <Space direction="vertical" size={14} className="fullWidth">
          <Text type="secondary">选择分析维度，对比商品标签指标数据。点击指标数值查看趋势图。</Text>
          <Select
            mode="multiple"
            placeholder="选择分析维度"
            value={selectedDims}
            onChange={setSelectedDims}
            options={TAG_DIMENSIONS.map((d) => ({ value: d.key, label: d.label }))}
            style={{ minWidth: 320 }}
          />
          <Table
            rowKey="sku_id"
            dataSource={filtered}
            pagination={{ pageSize: 10, showSizeChanger: true }}
            scroll={{ x: 980 }}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据，请先采集商品标签" /> }}
            columns={[
              {
                title: "商品",
                render: (_: unknown, row: MetricSummary) => (
                  <a href={`https://www.xiaohongshu.com/goods-detail/${row.sku_id}`} target="_blank" rel="noreferrer">
                    {row.title || row.sku_id}
                  </a>
                ),
              },
              { title: "销量", dataIndex: "sales_volume", width: 110, render: (v) => v || "-" },
              { title: "到手价", dataIndex: "deal_price", width: 100, render: (v) => v ? <Text strong>¥{v}</Text> : "-" },
              { title: "原价", dataIndex: "original_price", width: 100, render: (v) => v ? <Text delete type="secondary">¥{v}</Text> : "-" },
              { title: "店铺名称", dataIndex: "shop_name", width: 160, render: (v) => v || "-" },
              ...dimColumns,
              {
                title: "创建时间",
                dataIndex: "product_created_at",
                width: 170,
                sorter: (a: MetricSummary, b: MetricSummary) => a.product_created_at.localeCompare(b.product_created_at),
                render: (v) => v ? new Date(v).toLocaleString() : "-",
              },
              {
                title: "更新时间",
                dataIndex: "product_updated_at",
                width: 170,
                sorter: (a: MetricSummary, b: MetricSummary) => a.product_updated_at.localeCompare(b.product_updated_at),
                render: (v) => v ? new Date(v).toLocaleString() : "-",
              },
            ]}
          />
        </Space>
      </Card>
      <Modal
        title={`指标趋势 — ${chartSkuId || ""}`}
        open={!!chartSkuId}
        onCancel={() => setChartSkuId(null)}
        footer={null}
        width={720}
        destroyOnHidden
      >
        {chartSkuId && <TrendChart history={history} />}
      </Modal>
    </>
  );
}

function TrendChart({ history }: { history: MetricHistory[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !history.length) return;
    const chart = echarts.init(ref.current);
    const byDim: Record<string, { dates: string[]; values: number[] }> = {};
    for (const h of history) {
      const entry = byDim[h.dim_key] || (byDim[h.dim_key] = { dates: [], values: [] });
      entry.dates.push(new Date(h.created_at).toLocaleDateString());
      entry.values.push(h.dim_value);
    }
    const dims = Object.keys(byDim);
    const allDates = dims.length ? byDim[dims[0]].dates : [];
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: dims.map((k) => TAG_DIMENSIONS.find((d) => d.key === k)?.label || k) },
      xAxis: { type: "category", data: allDates },
      yAxis: { type: "value" },
      series: dims.map((dimKey) => ({
        name: TAG_DIMENSIONS.find((d) => d.key === dimKey)?.label || dimKey,
        type: "line",
        smooth: true,
        data: byDim[dimKey].values,
      })),
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.dispose(); };
  }, [history]);

  if (!history.length) return <Empty description="暂无历史数据" />;
  return <div ref={ref} style={{ width: "100%", height: 360 }} />;
}

function DevicesPage({ apiKey }: { apiKey: string }) {
  const [devices, setDevices] = useState<AndroidDevice[]>([]);
  const [statuses, setStatuses] = useState<AndroidDeviceStatus[]>([]);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [filters, setFilters] = useState<DeviceFilters>({ keyword: "" });
  const [form] = Form.useForm<DeviceFormValue>();
  const liveBySerial = useMemo(() => new Map(statuses.map((status) => [status.adb_serial, status])), [statuses]);
  const filteredDevices = useMemo(() => {
    const keyword = filters.keyword.trim().toLowerCase();
    return devices.filter((device) => {
      const live = liveBySerial.get(device.adb_serial);
      const online = live?.online_status || live?.status || "missing";
      const work = live?.busy ? "busy" : "idle";
      const haystack = [device.name, device.adb_serial, device.phone_ip, device.model].filter(Boolean).join(" ").toLowerCase();
      return (!keyword || haystack.includes(keyword)) && (!filters.online || online === filters.online) && (!filters.work || work === filters.work);
    });
  }, [devices, filters, liveBySerial]);

  async function load() {
    const [saved, statusData] = await Promise.all([api.listDevices(apiKey), api.deviceStatuses(apiKey)]);
    setDevices(saved);
    setStatuses(statusData.devices);
  }

  async function save(values: DeviceFormValue) {
    setError("");
    try {
      await api.createDevice({ ...values, ssh_remote_port: Number(values.ssh_remote_port) || null }, apiKey);
      setCreateOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function useDetected(device: AndroidDeviceStatus) {
    form.setFieldsValue({
      name: device.name || device.adb_serial,
      adb_serial: device.adb_serial,
      phone_ip: device.phone_ip || "",
      ssh_remote_port: device.ssh_remote_port ? String(device.ssh_remote_port) : "",
      model: device.model || "",
    });
    setCreateOpen(true);
  }

  useEffect(() => {
    form.setFieldsValue({
      name: "vivo V2048A",
      adb_serial: "127.0.0.1:15555",
      phone_ip: "192.168.2.83",
      ssh_remote_port: "15555",
      model: "PD2048",
    });
    load().catch(() => undefined);
  }, [apiKey]);

  return (
    <>
      <Card
        title="设备列表"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增设备</Button>
          </Space>
        }
      >
          <Row gutter={[10, 10]} className="listFilters">
            <Col xs={24} md={12}>
              <Input allowClear placeholder="搜索设备、serial、IP" value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} />
            </Col>
            <Col xs={12} md={6}>
              <Select
                allowClear
                className="fullWidth"
                placeholder="在线状态"
                value={filters.online}
                onChange={(value) => setFilters({ ...filters, online: value })}
                options={[
                  { value: "device", label: "在线" },
                  { value: "offline", label: "离线" },
                  { value: "missing", label: "未连接" },
                ]}
              />
            </Col>
            <Col xs={12} md={6}>
              <Select
                allowClear
                className="fullWidth"
                placeholder="占用状态"
                value={filters.work}
                onChange={(value) => setFilters({ ...filters, work: value })}
                options={[
                  { value: "idle", label: "闲置" },
                  { value: "busy", label: "占用" },
                ]}
              />
            </Col>
          </Row>
          <Table
            rowKey="id"
            dataSource={filteredDevices}
            pagination={{ pageSize: 10 }}
            scroll={{ x: 860 }}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无设备" /> }}
            columns={[
              { title: "设备名", dataIndex: "name" },
              { title: "ADB serial", dataIndex: "adb_serial" },
              { title: "手机 IP", dataIndex: "phone_ip", render: (value) => value || "-" },
              { title: "型号", dataIndex: "model", render: (value) => value || "-" },
              {
                title: "状态",
                render: (_: unknown, device: AndroidDevice) => {
                  const live = liveBySerial.get(device.adb_serial);
                  const online = live?.online_status || live?.status || "missing";
                  return (
                    <Space>
                      <Tag color={online === "device" ? "success" : "default"}>{online === "device" ? "在线" : "离线"}</Tag>
                      <Tag color={live?.busy ? "processing" : "default"}>{live?.busy ? "占用" : "闲置"}</Tag>
                    </Space>
                  );
                },
              },
              {
                title: "操作",
                width: 110,
                fixed: "right",
                render: (_: unknown, device: AndroidDevice) => (
                  <Button size="small" onClick={() => useDetected({ ...device, id: device.id, online_status: "missing", detail: "", busy: false, work_status: "idle" })}>编辑</Button>
                ),
              },
            ]}
          />
      </Card>
      <Modal title="新增设备" open={createOpen} onCancel={() => setCreateOpen(false)} footer={null} destroyOnHidden>
          <Space direction="vertical" size={16} className="fullWidth">
            {statuses.filter((item) => !item.id).length > 0 && (
              <List
                size="small"
                header="检测到未保存设备"
                dataSource={statuses.filter((item) => !item.id)}
                renderItem={(device) => (
                  <List.Item actions={[<Button size="small" onClick={() => useDetected(device)}>使用</Button>]}>
                    <List.Item.Meta title={device.name} description={device.adb_serial} />
                  </List.Item>
                )}
              />
            )}
            <Form form={form} layout="vertical" onFinish={save}>
              <Form.Item name="name" label="设备名" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="adb_serial" label="ADB serial" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="phone_ip" label="手机 IP"><Input /></Form.Item>
              <Form.Item name="ssh_remote_port" label="远程端口"><Input /></Form.Item>
              <Form.Item name="model" label="型号"><Input /></Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>保存设备</Button>
            </Form>
            {error && <Alert type="error" message={error} showIcon />}
          </Space>
      </Modal>
    </>
  );
}

function KeysPage({ apiKey }: { apiKey: string }) {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [created, setCreated] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [filters, setFilters] = useState<KeyFilters>({ keyword: "" });
  const [form] = Form.useForm<KeyFormValue>();
  const filteredKeys = useMemo(() => {
    const keyword = filters.keyword.trim().toLowerCase();
    return keys.filter((key) => {
      const haystack = [key.name, key.key_prefix, key.status].filter(Boolean).join(" ").toLowerCase();
      const permissionMatched =
        !filters.permission ||
        (filters.permission === "devices" && key.can_view_devices) ||
        (filters.permission === "keys" && key.can_manage_keys) ||
        (filters.permission === "basic" && !key.can_view_devices && !key.can_manage_keys);
      return (!keyword || haystack.includes(keyword)) && (!filters.status || key.status === filters.status) && permissionMatched;
    });
  }, [filters, keys]);

  async function load() {
    setKeys(await api.listKeys(apiKey));
  }

  async function create(values: KeyFormValue) {
    const dayCount = Number(values.days);
    const expiresAt = dayCount ? new Date(Date.now() + dayCount * 86400_000).toISOString() : null;
    const data = await api.createKey({
      name: values.name,
      expires_at: expiresAt,
      can_view_devices: !!values.can_view_devices,
      can_manage_keys: !!values.can_manage_keys,
    }, apiKey);
    setCreated(data.key);
    setCreateOpen(false);
    await load();
  }

  async function revoke(id: number) {
    await api.revokeKey(id, apiKey);
    await load();
  }

  useEffect(() => {
    form.setFieldsValue({ name: "operator", days: "30", can_view_devices: false, can_manage_keys: false });
    load().catch(() => undefined);
  }, [apiKey]);

  return (
    <>
      <Card
        title="密钥列表"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增密钥</Button>
          </Space>
        }
      >
          <Row gutter={[10, 10]} className="listFilters">
            <Col xs={24} md={12}>
              <Input allowClear placeholder="搜索名称或前缀" value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} />
            </Col>
            <Col xs={12} md={6}>
              <Select
                allowClear
                className="fullWidth"
                placeholder="状态"
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value })}
                options={[
                  { value: "active", label: "active" },
                  { value: "revoked", label: "revoked" },
                ]}
              />
            </Col>
            <Col xs={12} md={6}>
              <Select
                allowClear
                className="fullWidth"
                placeholder="权限"
                value={filters.permission}
                onChange={(value) => setFilters({ ...filters, permission: value })}
                options={[
                  { value: "basic", label: "基础" },
                  { value: "devices", label: "设备" },
                  { value: "keys", label: "密钥" },
                ]}
              />
            </Col>
          </Row>
          <Table
            rowKey="id"
            dataSource={filteredKeys}
            pagination={{ pageSize: 10 }}
            scroll={{ x: 760 }}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无密钥" /> }}
            columns={[
              { title: "名称", dataIndex: "name" },
              { title: "前缀", dataIndex: "key_prefix" },
              { title: "过期时间", dataIndex: "expires_at", render: (value) => value ? new Date(value).toLocaleString() : "无" },
              {
                title: "权限",
                render: (_: unknown, key: ApiKeyRecord) => (
                  <Space wrap>
                    {key.can_view_devices && <Tag color="blue">设备</Tag>}
                    {key.can_manage_keys && <Tag color="cyan">密钥</Tag>}
                    {!key.can_view_devices && !key.can_manage_keys && <Tag>基础</Tag>}
                  </Space>
                ),
              },
              { title: "状态", dataIndex: "status", render: (value) => <Tag color={value === "active" ? "success" : "default"}>{value}</Tag> },
              {
                title: "操作",
                width: 110,
                fixed: "right",
                render: (_: unknown, key: ApiKeyRecord) => key.status === "active" ? <Button size="small" onClick={() => revoke(key.id)}>停用</Button> : <Text type="secondary">-</Text>,
              },
            ]}
          />
      </Card>
      <Modal title="新增密钥" open={createOpen} onCancel={() => setCreateOpen(false)} footer={null} destroyOnHidden>
          <Space direction="vertical" size={16} className="fullWidth">
            <Text type="secondary">密钥只在创建时完整显示一次。</Text>
            <Form form={form} layout="vertical" onFinish={create}>
              <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="days" label="有效天数，0 为不过期"><Input /></Form.Item>
              <Form.Item name="can_view_devices" valuePropName="checked"><Checkbox>允许查看设备列表</Checkbox></Form.Item>
              <Form.Item name="can_manage_keys" valuePropName="checked"><Checkbox>允许管理密钥列表</Checkbox></Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>生成密钥</Button>
            </Form>
          </Space>
      </Modal>
      {created && (
        <Modal title="新密钥" open={!!created} onCancel={() => setCreated("")} footer={<Button type="primary" onClick={() => setCreated("")}>完成</Button>}>
          <Alert type="success" message="密钥只显示一次" description={<Typography.Text copyable>{created}</Typography.Text>} />
        </Modal>
      )}
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
