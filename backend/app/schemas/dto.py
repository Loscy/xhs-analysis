from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    expires_at: Optional[datetime] = None
    can_view_devices: bool = False
    can_manage_keys: bool = False


class ApiKeyCreated(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str
    expires_at: Optional[datetime]
    can_view_devices: bool
    can_manage_keys: bool
    status: str


class ApiKeyPublic(BaseModel):
    id: int
    name: str
    key_prefix: str
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    can_view_devices: bool
    can_manage_keys: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AndroidDeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    adb_serial: str = Field(min_length=1, max_length=80)
    phone_ip: Optional[str] = None
    ssh_remote_port: Optional[int] = None
    model: Optional[str] = None
    notes: Optional[str] = None


class AndroidDevicePublic(AndroidDeviceCreate):
    id: int
    status: str
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TagQueryResponse(BaseModel):
    ok: bool
    sku_id: str
    input: Optional[str] = None
    source: Optional[str] = None
    resolved_url: Optional[str] = None
    tags: list[str] = []
    items: list[dict] = []
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class TagQueryRecord(BaseModel):
    id: int
    sku_id: str
    status: str
    tags: Optional[list[str]]
    error_message: Optional[str]
    elapsed_ms: Optional[int]
    device_id: Optional[int] = None
    product_id: Optional[int] = None
    source_input: Optional[str] = None
    source_url: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    input: str = Field(min_length=1)
    type: str = "manual"
    title: Optional[str] = None
    include_detail: bool = False
    device_id: Optional[int] = None
    is_main: bool = True
    group_id: Optional[int] = None


class ProductPublic(BaseModel):
    id: int
    item_id: str
    source_input: Optional[str]
    source_url: Optional[str]
    type: str
    title: Optional[str]
    sales_volume: Optional[str] = None
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None
    shop_url: Optional[str] = None
    shop_location: Optional[str] = None
    web_status: str
    web_error: Optional[str] = None
    include_detail: bool
    detail_status: str
    status: str
    is_main: bool = True
    device_collected: bool = False
    original_price: Optional[str] = None
    deal_price: Optional[str] = None
    group_id: Optional[int] = None
    collected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    latest_query: Optional[TagQueryRecord] = None

    model_config = {"from_attributes": True}


class TagQueryCreate(BaseModel):
    input: Optional[str] = None
    product_id: Optional[int] = None
    device_id: Optional[int] = None
