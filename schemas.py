from pydantic import BaseModel, Field
from typing import Optional, Literal


class MedicalDeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=50)
    device_name: str = Field(..., min_length=3, max_length=255)  # tối thiểu 3 ký tự
    department: str = Field(..., min_length=1, max_length=100)   # không rỗng
    status: Optional[Literal["ACTIVE", "INACTIVE"]] = "ACTIVE"   # chỉ nhận 2 giá trị quy chuẩn