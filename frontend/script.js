const form = document.querySelector("#forecast-form");
const inputs = document.querySelector("#inputs");
const statusText = document.querySelector("#status");
const resultBox = document.querySelector("#result");
const submitButton = document.querySelector("#submit-button");

const numericFields = [
  "hr", "season", "holiday", "weathersit",
  "temp", "atemp", "hum", "windspeed"
];

function clearResult(message) {
  resultBox.hidden = true;
  statusText.classList.remove("error");
  statusText.textContent = message;
}

function clearFieldErrors() {
  for (const name of ["forecast_date", ...numericFields]) {
    form.elements.namedItem(name).setCustomValidity("");
  }
}

form.addEventListener("input", (event) => {
  if (typeof event.target.setCustomValidity === "function") {
    event.target.setCustomValidity("");
  }
  clearResult("Kịch bản đã thay đổi. Bấm Dự báo để cập nhật kết quả.");
});

document.querySelector("#sample-button").addEventListener("click", () => {
  const sample = {
    forecast_date: "2011-01-01",
    hr: 0,
    season: 1,
    holiday: 0,
    weathersit: 1,
    temp: 0.24,
    atemp: 0.2879,
    hum: 0.81,
    windspeed: 0.0
  };

  clearFieldErrors();

  for (const [name, value] of Object.entries(sample)) {
    form.elements.namedItem(name).value = value;
  }

  clearResult("Đã nạp kịch bản mẫu. Bấm Dự báo lượt thuê.");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!form.reportValidity()) return;

  const payload = {
    forecast_date: form.elements.namedItem("forecast_date").value
  };

  for (const name of numericFields) {
    payload[name] = Number(form.elements.namedItem(name).value);
  }

  clearResult("Đang tính dự báo…");
  inputs.disabled = true;
  submitButton.textContent = "Đang dự báo…";

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch("/api/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    const data = await response.json();

    if (!response.ok) {
      let message = "Không thể thực hiện dự báo.";

      if (Array.isArray(data.detail)) {
        message = data.detail.map((error) => {
          const name = error.loc?.at(-1);
          return `${name}: ${error.msg}`;
        }).join("; ");
      } else if (data.detail?.message) {
        message = `${data.detail.field}: ${data.detail.message}`;
      } else if (typeof data.detail === "string") {
        message = data.detail;
      }

      throw new Error(message);
    }

    document.querySelector("#prediction").textContent =
      new Intl.NumberFormat("vi-VN", {
        maximumFractionDigits: 1
      }).format(data.prediction);

    document.querySelector("#forecast-time").textContent =
      `Ngày ${data.forecast_date}, giờ ${data.hour}:00`;

    document.querySelector("#model-version").textContent =
      `Phiên bản mô hình: ${data.model_version}`;

    const warningList = document.querySelector("#warnings");
    warningList.replaceChildren();

    for (const warning of data.warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      warningList.appendChild(item);
    }

    document.querySelector("#technical-result").textContent =
      JSON.stringify(data, null, 2);

    resultBox.hidden = false;
    statusText.textContent = "Dự báo thành công.";
  } catch (error) {
    statusText.classList.add("error");
    statusText.textContent = error.name === "AbortError"
      ? "Yêu cầu quá thời gian. Hãy kiểm tra backend và thử lại."
      : error instanceof TypeError
        ? "Không kết nối được API. Hãy kiểm tra backend."
        : error.message;
  } finally {
    clearTimeout(timeout);
    inputs.disabled = false;
    submitButton.textContent = "Dự báo lượt thuê";
  }
});