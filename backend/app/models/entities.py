from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "xhs_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    can_view_devices: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_manage_keys: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AndroidDevice(Base):
    __tablename__ = "xhs_android_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    adb_serial: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    phone_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ssh_remote_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    app_package: Mapped[str] = mapped_column(String(120), default="com.xingin.xhs", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    queries: Mapped[list["TagQuery"]] = relationship(back_populates="device")


class ProductGroup(Base):
    __tablename__ = "xhs_product_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="group")


class Product(Base):
    __tablename__ = "xhs_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sales_volume: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    shop_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    shop_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    shop_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shop_location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    web_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    web_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    web_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    include_detail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail_status: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    device_collected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_price: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    deal_price: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("xhs_product_groups.id"), nullable=True)
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    group: Mapped[Optional["ProductGroup"]] = relationship(back_populates="products")


class TagQuery(Base):
    __tablename__ = "xhs_tag_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    raw_items: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    elapsed_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("xhs_android_devices.id"), nullable=True)
    api_key_id: Mapped[Optional[int]] = mapped_column(ForeignKey("xhs_api_keys.id"), nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("xhs_products.id"), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    device: Mapped[Optional[AndroidDevice]] = relationship(back_populates="queries")


class TagMetric(Base):
    __tablename__ = "xhs_tag_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dim_key: Mapped[str] = mapped_column(String(32), nullable=False)
    dim_value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
