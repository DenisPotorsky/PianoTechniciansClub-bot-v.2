from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    REFUNDED = "refunded"

@dataclass
class Payment:
    """Модель платежа"""
    id: int
    user_id: int
    amount: int
    status: PaymentStatus
    payment_id: str
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None