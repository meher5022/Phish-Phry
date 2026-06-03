console.log("🟢 PhishPhry content.js loaded");

let hoverTimer = null;
let tooltip = null;
let activeLink = null;

const urlCache = {};

// Detect hover on links
document.addEventListener("mouseover", (event) => {
  const link = event.target.closest("a");
  if (!link || !link.href) return;

  // Prevent re-trigger on same link
  if (link === activeLink) return;
  activeLink = link;

  console.log("🔍 Hovered URL:", link.href);

  hoverTimer = setTimeout(() => {
    checkURL(link.href, link);
  }, 500);
});

document.addEventListener("mouseout", (event) => {
  const link = event.target.closest("a");
  if (!link || link !== activeLink) return;

  clearTimeout(hoverTimer);

  // Reset cursor state
  document.body.classList.remove("phishphry-danger");
  document.body.classList.add("phishphry-safe");

  removeTooltip();
  activeLink = null;
});

// Send URL to background script
function checkURL(url, linkElement) {
  if (urlCache[url]) {
    showResult(urlCache[url], linkElement);
    return;
  }

  console.log("📤 Sending URL to background:", url);

  chrome.runtime.sendMessage(
    {
      type: "CHECK_URL",
      url: url
    },
    (response) => {
      if (!response) return;

      console.log("📥 Result from background:", response);

      urlCache[url] = response;
      showResult(response, linkElement);
    }
  );
}

// Tooltip + cursor logic
function showResult(result, link) {
  removeTooltip();

  // 🐡 Cursor state via body class (NOT inline)
  document.body.classList.remove("phishphry-safe", "phishphry-danger");

  if (result.status === "phishing" || result.subtype === "suspicious") {
    document.body.classList.add("phishphry-danger");
  } else {
    document.body.classList.add("phishphry-safe");
  }

  // Tooltip
  tooltip = document.createElement("div");
  tooltip.style.position = "absolute";
  tooltip.style.padding = "6px 10px";
  tooltip.style.fontSize = "12px";
  tooltip.style.color = "#fff";
  tooltip.style.borderRadius = "6px";
  tooltip.style.zIndex = "999999";
  tooltip.style.pointerEvents = "none";
  tooltip.style.background =
    result.status === "phishing" ? "#e74c3c" : "#2ecc71";

  tooltip.innerText =
    result.status === "phishing"
      ? `⚠️ Phishing (${result.subtype || "detected"})`
      : "✅ Legitimate";

  document.body.appendChild(tooltip);

  const rect = link.getBoundingClientRect();
  tooltip.style.top = `${rect.top + window.scrollY - 30}px`;
  tooltip.style.left = `${rect.left + window.scrollX}px`;
}

// Remove tooltip
function removeTooltip() {
  if (tooltip) {
    tooltip.remove();
    tooltip = null;
  }
}
