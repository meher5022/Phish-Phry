console.log("🟢 PhishPhry cursor system loaded");

// Inject cursor styles (ONCE)
const style = document.createElement("style");
style.textContent = `
  /* Default (safe) cursor */
  body.phishphry-safe,
  body.phishphry-safe * {
    cursor: url(${chrome.runtime.getURL("cursor64.png")}) 32 32, auto !important;
  }

  /* Suspicious / phishing cursor */
  body.phishphry-danger,
  body.phishphry-danger * {
    cursor: url(${chrome.runtime.getURL("puff64.png")}) 32 32, auto !important;
  }
`;
document.head.appendChild(style);

// Set default cursor state
document.body.classList.add("phishphry-safe");
