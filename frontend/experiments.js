(() => {
  "use strict";

  const status = document.querySelector("#experiments-status");
  const splitStatus = document.querySelector("#split-status");
  const chart = document.querySelector("#sgd-chart");
  const chartStatus = document.querySelector("#sgd-chart-status");

  function number(value, digits = 2) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return "Không có dữ liệu";
    }
    return new Intl.NumberFormat("vi-VN", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    }).format(value);
  }

  function learningRate(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return "Không có dữ liệu";
    }
    return new Intl.NumberFormat("vi-VN", {
      maximumSignificantDigits: 15
    }).format(value);
  }

  function table(body, rows, values) {
    const fragment = document.createDocumentFragment();
    for (const item of rows) {
      const row = document.createElement("tr");
      for (const value of values(item)) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      fragment.appendChild(row);
    }
    body.replaceChildren(fragment);
  }

  chart.addEventListener("load", () => {
    chartStatus.textContent = "Biểu đồ SGD từ báo cáo đã lưu.";
  });
  chart.addEventListener("error", () => {
    chart.hidden = true;
    chartStatus.classList.add("error");
    chartStatus.textContent =
      "Không tải được biểu đồ SGD. Hãy kiểm tra báo cáo sgd_learning_curves.png.";
  });
  chart.src = "/api/experiments/sgd-chart";

  async function loadExperiments() {
    try {
      const response = await fetch("/api/experiments");
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string"
          ? data.detail : "Không tải được báo cáo thí nghiệm.");
      }
      if (!Array.isArray(data.sgd) || !data.sgd.length ||
          !Array.isArray(data.split_comparison) || !data.split_comparison.length) {
        throw new Error("Báo cáo thí nghiệm trống hoặc không đúng định dạng.");
      }

      table(document.querySelector("#sgd-body"), data.sgd, row => [
        learningRate(row.learning_rate), number(row.epochs, 0), number(row.seed, 0),
        number(row.MAE), number(row.RMSE), number(row.R2, 4)
      ]);
      table(document.querySelector("#split-body"), data.split_comparison, row => [
        row.split ?? "Không có dữ liệu", row.model ?? "Không có dữ liệu",
        number(row.train_rows, 0), number(row.validation_rows, 0),
        number(row.MAE), number(row.RMSE), number(row.R2, 4)
      ]);
      status.textContent = "Đã tải kết quả SGD trên validation từ báo cáo đã lưu.";
      splitStatus.textContent = "Đã tải kết quả so sánh cách chia trên validation.";
    } catch (error) {
      const message = error instanceof TypeError
        ? "Không kết nối được API thí nghiệm. Hãy kiểm tra backend và thử tải lại trang."
        : error instanceof SyntaxError
          ? "API thí nghiệm trả dữ liệu không hợp lệ. Hãy kiểm tra backend."
          : error.message;
      for (const element of [status, splitStatus]) {
        element.classList.add("error");
        element.textContent = message;
      }
    }
  }

  loadExperiments();
})();
