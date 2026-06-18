"""سكيمات الاشتراكات (Google Play Billing)."""
from datetime import datetime

from pydantic import BaseModel, Field


class VerifyPurchaseRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=120)
    purchase_token: str = Field(..., min_length=1, max_length=512)


class BillingStatusOut(BaseModel):
    is_premium: bool
    status: str
    product_id: str | None = None
    current_period_end: datetime | None = None
    auto_renewing: bool = False
