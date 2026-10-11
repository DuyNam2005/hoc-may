const statusText = document.querySelector("#evaluation-status");
const content = document.querySelector("#evaluation-content");

const groupNames = {
  All: "Tất cả",
  Peak_workingday: "Giờ cao điểm ngày làm việc",
  Other_hours: "Các giờ còn lại",
  Bad_weather: "Thời tiết xấu (3 hoặc 4)",
  Weather_1: "Thời tiết loại 1",
  Weather_2: "Thời tiết loại 2",
  Weather_3: "Thời tiết loại 3",
  Weather_4: "Thời tiết loại 4"
};

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined) return "Chưa có mẫu";

  return new Intl.NumberFormat("vi-VN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

function appendRow(body, values) {
  const row = document.createElement("tr");

  for (const value of values) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  }

  body.appendChild(row);
}

async function loadEvaluation() {
  try {
    const response = await fetch("/api/evaluation");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Không tải được kết quả đánh giá.");
    }

    const model = data.metrics.LinearRegression;
    const baseline = data.metrics.Baseline;

    document.querySelector("#test-period").textContent =
      `Test: ${data.test_start} → ${data.test_end} · ` +
      `${formatNumber(data.test_rows, 0)} giờ có dữ liệu · ` +
      `Mô hình phiên bản ${data.model_version}`;

    document.querySelector("#metric-mae").textContent =
      formatNumber(model.MAE);
    document.querySelector("#metric-rmse").textContent =
      formatNumber(model.RMSE);
    document.querySelector("#metric-r2").textContent =
      formatNumber(model.R2, 4);

    const comparisonBody = document.querySelector("#comparison-body");
    comparisonBody.replaceChildren();

    for (const [name, metrics] of Object.entries(data.metrics)) {
      appendRow(comparisonBody, [
        name,
        formatNumber(metrics.MAE),
        formatNumber(metrics.RMSE),
        formatNumber(metrics.R2, 4)
      ]);
    }

    const improvementText = document.querySelector("#mae-improvement");

    if (baseline.MAE > 0) {
      const change = 100 * (baseline.MAE - model.MAE) / baseline.MAE;
      improvementText.textContent = change >= 0
        ? `MAE giảm ${formatNumber(change, 1)}% so với baseline.`
        : `MAE tăng ${formatNumber(-change, 1)}% so với baseline.`;
    } else {
      improvementText.textContent =
        "Không tính mức thay đổi phần trăm khi MAE baseline bằng 0.";
    }

    const groupsBody = document.querySelector("#groups-body");
    groupsBody.replaceChildren();

    for (const row of data.group_metrics) {
      appendRow(groupsBody, [
        row.model,
        groupNames[row.group] || row.group,
        formatNumber(row.n, 0),
        formatNumber(row.MAE),
        formatNumber(row.RMSE),
        formatNumber(row.bias)
      ]);
    }

    const chart = document.querySelector("#test-chart");
    chart.addEventListener("error", () => {
      chart.hidden = true;
      document.querySelector("#chart-status").textContent =
        "Chưa tải được biểu đồ. Hãy kiểm tra tệp test_first_week.png.";
    });
    chart.src = "/api/evaluation/chart";

    content.hidden = false;
    statusText.textContent = "Đã tải kết quả đánh giá đã lưu.";
  } catch (error) {
    statusText.classList.add("error");
    statusText.textContent = error instanceof TypeError
      ? "Không kết nối được API. Hãy kiểm tra backend."
      : error.message;
  }
}

loadEvaluation();