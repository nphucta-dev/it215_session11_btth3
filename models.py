import enum
from sqlalchemy import Column, Integer, String, Enum
from database import Base


class DeviceStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MedicalDeviceModel(Base):
    __tablename__ = "medical_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_code = Column(String(50), unique=True, nullable=False)
    device_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    status = Column(
        Enum(DeviceStatusEnum, name="status_enum"),
        nullable=False,
        default=DeviceStatusEnum.ACTIVE
    )