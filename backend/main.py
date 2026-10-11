import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


class ForecastInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
    )

    forecast_date: date = Field(
        description="Ngày kịch bản, thuộc giai đoạn 2011–2012"
    )
    hr: int = Field(ge=0, le=23, strict=True)
    season: int = Field(
        ge=1, le=4, strict=True,
        description="Mã mùa theo dữ liệu gốc"
    )
    holiday: int = Field(ge=0, le=1, strict=True)
    weathersit: int = Field(ge=1, le=4, strict=True)

    temp: float = Field(
        ge=0, le=1, description="Nhiệt độ chuẩn hóa, không phải °C"
    )
    atemp: float = Field(
        ge=0, le=1, description="Nhiệt độ cảm nhận chuẩn hóa"
    )
    hum: float = Field(
        ge=0, le=1, description="Độ ẩm chuẩn hóa; 0.8 tương ứng 80%"
    )
    windspeed: float = Field(
        ge=0, le=1, description="Tốc độ gió chuẩn hóa"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    models_dir = PROJECT_ROOT / "models"

    with (models_dir / "model_config.json").open(
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    pipeline_path = models_dir / "forecast_pipeline.joblib"
    actual_hash = hashlib.sha256(
        pipeline_path.read_bytes()
    ).hexdigest()

    if actual_hash != config["pipeline_sha256"]:
        raise RuntimeError("Pipeline không khớp cấu hình đã chốt.")

    if config["prediction_policy"] != "maximum(raw_prediction, 0)":
        raise RuntimeError("Quy tắc đầu ra không khớp.")

    app.state.pipeline = joblib.load(pipeline_path)
    app.state.model_config = config
    yield


app = FastAPI(
    title="BikeDemand API",
    description="Demo dự báo lượt thuê theo giờ từ dữ liệu lịch sử.",
    version="1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": app.state.model_config["model_name"],
        "model_version": app.state.model_config["model_version"],
    }


@app.post("/api/forecast")
def forecast(payload: ForecastInput):
    if payload.forecast_date.year not in (2011, 2012):
        raise HTTPException(
            status_code=422,
            detail={
                "field": "forecast_date",
                "message": "Bản demo chỉ hỗ trợ kịch bản năm 2011–2012.",
            },
        )

    # Python: thứ Hai=0; dữ liệu này: Chủ nhật=0.
    weekday = (payload.forecast_date.weekday() + 1) % 7
    workingday = int(
        weekday not in (0, 6) and payload.holiday == 0
    )

    features = {
        "season": payload.season,
        "yr": payload.forecast_date.year - 2011,
        "mnth": payload.forecast_date.month,
        "hr": payload.hr,
        "holiday": payload.holiday,
        "weekday": weekday,
        "workingday": workingday,
        "weathersit": payload.weathersit,
        "temp": payload.temp,
        "atemp": payload.atemp,
        "hum": payload.hum,
        "windspeed": payload.windspeed,
    }

    config = app.state.model_config
    frame = pd.DataFrame([features], columns=config["features"])

    # Kiểm tra các nhóm đã được encoder học từ train.
    preprocessor = app.state.pipeline.named_steps["preprocessor"]
    encoder = preprocessor.named_transformers_["categorical"]
    categorical_columns = preprocessor.transformers_[0][2]

    for column, categories in zip(
        categorical_columns, encoder.categories_
    ):
        if features[column] not in categories:
            raise HTTPException(
                status_code=422,
                detail={
                    "field": column,
                    "message": "Giá trị chưa xuất hiện trong train.",
                },
            )

    try:
        raw_prediction = float(
            app.state.pipeline.predict(frame)[0]
        )
    except Exception:
        logger.exception("Forecast failed")
        raise HTTPException(
            status_code=500,
            detail="Không thể tạo dự báo. Hãy kiểm tra log backend.",
        )

    if not np.isfinite(raw_prediction):
        raise HTTPException(
            status_code=500,
            detail="Mô hình trả kết quả không hợp lệ.",
        )

    prediction = max(raw_prediction, 0.0)

    warnings = [
        "Demo dùng dữ liệu lịch sử 2011–2012; chưa xác thực cho hiện tại.",
        "Các biến thời tiết là kịch bản do người dùng cung cấp.",
    ]

    if workingday and payload.hr in config["peak_hours"]:
        warnings.append(
            "Mô hình có xu hướng dự báo thấp ở giờ cao điểm."
        )

    if payload.weathersit in config["bad_weather_codes"]:
        warnings.append(
            "MAE thời tiết xấu chưa tốt hơn baseline trong đánh giá."
        )

    if payload.weathersit == 4:
        warnings.append(
            "Thời tiết loại 4 có rất ít mẫu train và không có mẫu "
            "validation/test; chưa đủ bằng chứng đánh giá."
        )

    if raw_prediction < 0:
        warnings.append(
            "Dự báo gốc âm đã được đưa về 0 theo quy tắc đã chốt."
        )

    return {
        "forecast_date": payload.forecast_date.isoformat(),
        "hour": payload.hr,
        "prediction": prediction,
        "raw_prediction": raw_prediction,
        "unit": "lượt thuê/giờ",
        "model_version": config["model_version"],
        "features_used": features,
        "warnings": warnings,
    }

FRONTEND_DIR = PROJECT_ROOT / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api/evaluation")
def evaluation():
    result_path = PROJECT_ROOT / "reports" / "test_metrics.json"

    if not result_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Chưa có kết quả đánh giá test.",
        )

    with result_path.open(encoding="utf-8") as file:
        result = json.load(file)

    config = app.state.model_config
    if result["pipeline_sha256"] != config["pipeline_sha256"]:
        raise HTTPException(
            status_code=503,
            detail="Kết quả đánh giá không khớp mô hình đang phục vụ.",
        )

    return result


@app.get("/api/evaluation/chart", include_in_schema=False)
def evaluation_chart():
    chart_path = (
        PROJECT_ROOT / "reports" / "figures" / "test_first_week.png"
    )

    if not chart_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Chưa có biểu đồ đánh giá.",
        )

    return FileResponse(chart_path, media_type="image/png")


@app.get("/evaluation", include_in_schema=False)
def evaluation_page():
    return FileResponse(FRONTEND_DIR / "evaluation.html")

@app.get("/api/model-card")
def model_card():
    config = app.state.model_config

    return {
        "model_name": config["model_name"],
        "model_version": config["model_version"],
        "features": config["features"],
        "validation_metrics": config["validation_metrics"],
        "peak_hours": config["peak_hours"],
        "train_start": config["train_start"],
        "train_end": config["train_end"],
        "validation_start": config["validation_start"],
        "validation_end": config["validation_end"],
        "test_start": config["test_start"],
        "test_end": config["test_end"],
        "prediction_policy": config["prediction_policy"],
    }


@app.get("/about", include_in_schema=False)
def about_page():
    return FileResponse(FRONTEND_DIR / "about.html")

@app.get("/api/experiments")
def experiments():
    reports_dir = PROJECT_ROOT / "reports"
    return {
        "sgd": read_experiment_report(
            reports_dir / "sgd_validation_metrics.csv",
            ["learning_rate", "epochs", "seed", "MAE", "RMSE", "R2"],
        ),
        "split_comparison": read_experiment_report(
            reports_dir / "split_comparison.csv",
            ["split", "model", "train_rows", "validation_rows", "MAE", "RMSE", "R2"],
            text_columns=("split", "model"),
        ),
    }


def read_experiment_report(path: Path, columns, text_columns=()):
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Thiếu báo cáo thí nghiệm: {path.name}.",
        )

    try:
        frame = pd.read_csv(path)
        missing_columns = set(columns) - set(frame.columns)
        if missing_columns:
            raise ValueError("thiếu cột " + ", ".join(sorted(missing_columns)))
        if frame.empty:
            raise ValueError("báo cáo không có bản ghi")
        for column in columns:
            if column not in text_columns:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
        # JSON không hỗ trợ NaN/Infinity; biểu diễn các giá trị này bằng null.
        frame = frame.replace([np.inf, -np.inf], np.nan).astype(object)
        return frame.where(pd.notna(frame), None).to_dict(orient="records")
    except (OSError, ValueError, pd.errors.ParserError) as error:
        logger.warning("Cannot read experiment report %s: %s", path.name, error)
        raise HTTPException(
            status_code=503,
            detail=f"Không thể đọc báo cáo thí nghiệm {path.name}: dữ liệu hoặc cột không hợp lệ.",
        ) from error


@app.get("/api/experiments/sgd-chart", include_in_schema=False)
def sgd_chart():
    chart_path = (
        PROJECT_ROOT / "reports" / "figures"
        / "sgd_learning_curves.png"
    )

    if not chart_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Chưa có biểu đồ SGD.",
        )

    return FileResponse(chart_path, media_type="image/png")
