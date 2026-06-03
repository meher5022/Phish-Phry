console.log("🟢 PhishPhry background.js running");

chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({ url: "dashboard.html" });
});


// Initialize stats
function initializeStats() {
  chrome.storage.local.get("stats", (data) => {
    if (!data.stats) {
      chrome.storage.local.set({
        stats: {
          totalScanned: 0,
          totalMalicious: 0,
          usersProtected: 1,
          logs: []
        }
      });
    }
  });
}

chrome.runtime.onInstalled.addListener(initializeStats);
chrome.runtime.onStartup.addListener(initializeStats);

// Handle hover-based URL checking (ML backend)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

  // 🔍 Hover detection → ML backend
  if (message.type === "CHECK_URL") {
    fetch("http://127.0.0.1:5000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: message.url })
    })
      .then(res => res.json())
      .then(data => {
        let result;

        if (data.type === "phishing") {
          result = {
            status: "phishing",
            subtype: data.subtype || "Unknown"
          };
        } else {
          result = { status: "safe" };
        }

        sendResponse(result);
      })
      .catch(err => {
        console.error("Backend error:", err);
        sendResponse(null);
      });

    return true;
  }

  // 📊 Logging + dashboard stats
  if (message.type === "LINK_EVENT") {
    chrome.storage.local.get("stats", (data) => {
      const stats = data.stats;

      const isMalicious = message.category === "Phishing";

      stats.totalScanned += 1;
      if (isMalicious) stats.totalMalicious += 1;

      stats.logs.push({
        url: message.url,
        category: message.category || "Unknown",
        isMalicious,
        timestamp: message.timestamp
      });

      chrome.storage.local.set({ stats }, () => {
        sendResponse({ status: "stored" });
      });
    });

    return true;
  }
});
