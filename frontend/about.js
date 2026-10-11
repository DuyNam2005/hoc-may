const statusText = document.querySelector("#model-status");
const content = document.querySelector("#model-content");

function formatNumber(value) {
  return new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 4
  }).format(value);
}

async function loadModelCard() {
  try {
    const response = await fetch("/api/model-card");
    const data = await response.json();

    if (!response.ok) {
      throw new Error("Không tải được thông tin mô hình.");
    }

    document.querySelector("#model-name").textContent =
      `Mô hình: ${data.model_name} · Phiên bản: ${data.model_version}`;

    document.querySelector("#model-features").textContent =
      data.features.join(", ");

    const splitBody = document.querySelector("#split-body");
    splitBody.replaceChildren();

    const splits = [
      ["Train", data.train_start, data.train_end],
      ["Validation", data.validation_start, data.validation_end],
      ["Test", data.test_start, data.test_end]
    ];

    for (const values of splits) {
      const row = document.createElement("tr");
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      splitBody.appendChild(row);
    }

    const metrics = data.validation_metrics;
    document.querySelector("#validation-summary").textContent =
      `Validation: MAE ${formatNumber(metrics.MAE)} lượt/giờ; ` +
      `RMSE ${formatNumber(metrics.RMSE)} lượt/giờ; ` +
      `R² ${formatNumber(metrics.R2)}.`;

    document.querySelector("#peak-definition").textContent =
      `Giờ cao điểm gồm ${data.peak_hours.join(", ")} giờ ` +
      `trên ngày làm việc, được chọn từ bốn giờ có nhu cầu ` +
      `trung bình cao nhất trong train.`;

    content.hidden = false;
    statusText.textContent = "Đã tải thông tin mô hình đang phục vụ.";
  } catch (error) {
    statusText.classList.add("error");
    statusText.textContent = error instanceof TypeError
      ? "Không kết nối được API. Hãy kiểm tra backend."
      : error.message;
  }
}

loadModelCard();