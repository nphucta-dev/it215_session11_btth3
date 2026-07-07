from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timezone

from database import get_db
from models import MedicalDeviceModel
from schemas import MedicalDeviceCreate

app = FastAPI()


# ----------------- HELPER -----------------
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_response(status_code: int, message: str, error, data, path: str):
    return {
        "statusCode": status_code,
        "message": message,
        "error": error,
        "data": data,
        "path": path,
        "timestamp": now_iso()
    }


def serialize_device(device: MedicalDeviceModel):
    return {
        "id": device.id,
        "device_code": device.device_code,
        "device_name": device.device_name,
        "department": device.department,
        "status": device.status.value if hasattr(device.status, "value") else device.status
    }


# ----------------- GLOBAL EXCEPTION HANDLERS -----------------
# Đảm bảo mọi lỗi (business hoặc validation) đều trả đúng cấu trúc 6 trường,
# không lộ Stack Trace thô ra ngoài — đặc biệt quan trọng với hệ thống bệnh viện.

ERROR_TEXT_MAP = {
    400: "Bad Request",
    404: "Not Found",
    422: "Unprocessable Entity",
    500: "Internal Server Error"
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=build_response(
            status_code=exc.status_code,
            message=exc.detail,
            error=ERROR_TEXT_MAP.get(exc.status_code, "Error"),
            data=None,
            path=str(request.url.path)
        )
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Bắt lỗi validate Pydantic (device_name < 3 ký tự, department rỗng, status sai ENUM...)
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = f"Dữ liệu không hợp lệ tại trường '{field}': {first_error['msg']}"

    return JSONResponse(
        status_code=422,
        content=build_response(
            status_code=422,
            message=message,
            error="Unprocessable Entity",
            data=None,
            path=str(request.url.path)
        )
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=build_response(
            status_code=500,
            message="Lỗi hệ thống, vui lòng thử lại sau",
            error="Internal Server Error",
            data=None,
            path=str(request.url.path)
        )
    )


# ----------------- API ENDPOINTS -----------------

@app.post("/devices", status_code=201)
def create_device(payload: MedicalDeviceCreate, request: Request, db: Session = Depends(get_db)):
    new_device = MedicalDeviceModel(
        device_code=payload.device_code,
        device_name=payload.device_name,
        department=payload.department,
        status=payload.status
    )

    try:
        db.add(new_device)
        db.commit()
        db.refresh(new_device)

    except IntegrityError:
        # Bẫy dữ liệu: device_code trùng lặp -> vi phạm ràng buộc UNIQUE
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Device code already exists"
        )

    except SQLAlchemyError:
        # Nghẽn mạch mạng / lỗi hệ thống khi commit -> rollback ngay để bảo vệ dữ liệu bệnh viện
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Lỗi hệ thống khi lưu dữ liệu"
        )

    return JSONResponse(
        status_code=201,
        content=build_response(
            status_code=201,
            message="Thêm thiết bị y tế thành công",
            error=None,
            data=serialize_device(new_device),
            path=str(request.url.path)
        )
    )


@app.get("/devices")
def get_all_devices(request: Request, db: Session = Depends(get_db)):
    devices = db.query(MedicalDeviceModel).all()  # API danh sách -> dùng .all() hợp lý
    data = [serialize_device(d) for d in devices]

    return JSONResponse(
        status_code=200,
        content=build_response(
            status_code=200,
            message="Lấy danh sách thiết bị y tế thành công",
            error=None,
            data=data,
            path=str(request.url.path)
        )
    )


@app.get("/devices/{device_id}")
def get_device_detail(device_id: int, request: Request, db: Session = Depends(get_db)):
    # Tối ưu: chỉ SELECT đúng 1 bản ghi qua .filter().first()
    device = db.query(MedicalDeviceModel).filter(MedicalDeviceModel.id == device_id).first()

    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    return JSONResponse(
        status_code=200,
        content=build_response(
            status_code=200,
            message="Lấy thông tin thiết bị y tế thành công",
            error=None,
            data=serialize_device(device),
            path=str(request.url.path)
        )
    )