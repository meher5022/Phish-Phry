  console.log("dashboard.js loaded");

  Chart.defaults.font.family = "'Roboto', sans-serif";  // <-- changed from Inter  Chart.defaults.font.size = 12;
  Chart.defaults.color = "#555";

  // ================== GLOBAL STATE ==================
  let logs = [];
  let darkMode = false;

  // ================== ELEMENTS ==================
  const startDate = document.getElementById("startDate");
  const endDate = document.getElementById("endDate");
  const categoryFilter = document.getElementById("categoryFilter");

  const applyBtn = document.getElementById("applyFilters");
  const darkBtn = document.getElementById("toggleDark");

  const checkBtn = document.getElementById("checkUrlBtn");
  const checkInput = document.getElementById("checkUrlInput");
  const checkResult = document.getElementById("checkResult");

  const logTable = document.getElementById("logTable");

  // KPIs
  const totalScanned = document.getElementById("totalScanned");
  const totalMalicious = document.getElementById("totalMalicious");
  const totalSafe = document.getElementById("totalSafe");
  const successRate = document.getElementById("successRate");
  const avgRisk = document.getElementById("avgRisk");

  // Charts
  let barChart = null;
  let pieChart = null;
  let lineChart = null;

  // Color palette
  let brownPalette = [
    "#7A5A3A",
    "#C1A27A",
    "#E6D3B1"
  ];

  // ================== STORAGE RETRIEVAL ==================
  chrome.storage.local.get(["logs", "darkMode"], (data) => {
    logs = data.logs || [];
    darkMode = data.darkMode || false;

    if (darkMode) document.body.classList.add("dark-mode");

    renderAll();
  });

  // ================== EVENT LISTENERS ==================
applyBtn.addEventListener("click", () => {
  const start = startDate.value;
  const end = endDate.value;

  // 1️⃣ Check both dates are selected
  if (!start || !end) {
    alert("Please select both start and end dates.");
    return;
  }

  // 2️⃣ Start date must not be after end date
  if (start > end) {
    alert("Start date cannot be after End date.");
    return;
  }

  // 3️⃣ Optional: prevent future dates
  const today = new Date().toISOString().slice(0, 10);
  if (start > today || end > today) {
    alert("Dates cannot be in the future.");
    return;
  }

  // 4️⃣ Optional: limit date range (e.g., 30 days max)
  const startObj = new Date(start);
  const endObj = new Date(end);
  const diffDays = (endObj - startObj) / (1000 * 60 * 60 * 24);
  if (diffDays > 30) {
    alert("Date range cannot exceed 30 days.");
    return;
  }

  // ✅ All checks passed
  renderAll();
});
  darkBtn.addEventListener("click", () => {
    darkMode = !darkMode;
    document.body.classList.toggle("dark-mode", darkMode);
    chrome.storage.local.set({ darkMode });
  });

  // ================== CHECK URL ==================
  checkBtn.addEventListener("click", async () => {
    const url = checkInput.value.trim();
    if (!url) return;

    try {
      const response = await fetch("http://localhost:5000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      const result = await response.json();
      const parsed = parseBackendResult(result);

      parsed.url = url;
      parsed.time = new Date().toISOString();

      logs.unshift(parsed);
      chrome.storage.local.set({ logs });

      showCheckResult(parsed);
      renderAll();

    } catch (err) {
      console.error("Backend error:", err);
      alert("Backend not running or unreachable.");
    }
  });

  // ================== PARSE BACKEND RESULT ==================
  function parseBackendResult(result) {
    if (result.type === "legitimate") {
      return {
        category: "Safe",
        risk: null,          // ⬅️ no risk %
        status: "Safe"
      };
    }

    if (result.type === "phishing") {
      return {
        category: result.subtype === "malware" ? "Malware" : "Phishing",
        risk: Math.round(result.risk_percent),
        status: "Malicious"
      };
    }

    return {
      category: "Unknown",
      risk: null,
      status: "Unknown"
    };
  }
  // ================== UI HELPERS ==================
  function showCheckResult(entry) {
    checkResult.classList.remove("hidden");

    if (entry.risk === null) {
      checkResult.innerHTML = `<b>${entry.category}</b> — Safe`;
    } else {
      checkResult.innerHTML = `<b>${entry.category}</b> — Risk ${entry.risk}%`;
    }

    setTimeout(() => {
      checkResult.classList.add("hidden");
    }, 5000);
  }

  // ================== FILTER LOGS ==================
  function getFilteredLogs() {
    return logs.filter(log => {
      const date = new Date(log.time).toISOString().slice(0, 10);

      if (startDate.value && date < startDate.value) return false;
      if (endDate.value && date > endDate.value) return false;

      const selected = [...categoryFilter.selectedOptions].map(o => o.value);
      if (selected.length && !selected.includes(log.category)) return false;

      return true;
    });
  }

  // ================== RENDER ALL ==================
  function renderAll() {
    const filtered = getFilteredLogs();
    renderTable(filtered);
    renderKPIs(filtered);
    renderCharts(filtered);
  }

  // ================== TABLE ==================
  function renderTable(data) {
    logTable.innerHTML = "";
    data.forEach(log => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${log.url}</td>
        <td>${log.category}</td>
        <td>${log.status}</td>
        <td>${new Date(log.time).toLocaleString()}</td>
      `;
      logTable.appendChild(row);
    });
  }

  // ================== KPIs ==================
  function renderKPIs(data) {
    const total = data.length;
    const malicious = data.filter(d => d.status === "Malicious").length;
    const safe = data.filter(d => d.status === "Safe").length;
    const avg = total ? Math.round(data.reduce((s, d) => s + d.risk, 0) / total) : 0;

    totalScanned.innerText = total;
    totalMalicious.innerText = malicious;
    totalSafe.innerText = safe;
    successRate.innerText = total ? `${Math.round((safe / total) * 100)}%` : "0%";
    avgRisk.innerText = `${avg}%`;
  }

  // ================== CHARTS ==================
  function destroyCharts() {
    if (barChart) barChart.destroy();
    if (pieChart) pieChart.destroy();
    if (lineChart) lineChart.destroy();
  }

  function renderCharts(data) {
    const counts = { Safe: 0, Phishing: 0, Malware: 0, IDN: 0 };
    data.forEach(d => counts[d.category] = (counts[d.category] || 0) + 1);

    destroyCharts();

    barChart = new Chart(document.getElementById("barChart"), {
      type: "bar",
      data: {
        labels: Object.keys(counts),
        datasets: [{
          data: Object.values(counts),
          backgroundColor: brownPalette
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });

    pieChart = new Chart(document.getElementById("pieChart"), {
      type: "pie",
      data: {
        labels: Object.keys(counts),
        datasets: [{ data: Object.values(counts), backgroundColor: brownPalette }]
      }
    });

    lineChart = new Chart(document.getElementById("lineChart"), {
      type: "line",
      data: {
        labels: data.map(d => new Date(d.time).toLocaleTimeString()),
        datasets: [{
          data: data.map(d => d.risk),
          fill: true,
          borderColor: "#7A5A3A",
          backgroundColor: "rgba(122,90,58,0.2)",
          tension: 0.3
        }]
      },
      options: { scales: { y: { beginAtZero: true, max: 100 } } }
    });
  }