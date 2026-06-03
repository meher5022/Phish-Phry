document.getElementById("scanBtn").addEventListener("click", async () => {
    const resultDiv = document.getElementById("result");
  
    // Loading state
    resultDiv.textContent = "Scanning current URL...";
    resultDiv.className = "result";
  
    try {
      chrome.tabs.query({ active: true, lastFocusedWindow: true }, async (tabs) => {
        if (!tabs || !tabs[0] || !tabs[0].url) {
          resultDiv.textContent = "Unable to read URL";
          resultDiv.className = "result phishing";
          return;
        }
  
        const url = tabs[0].url;
  
        const res = await fetch("http://127.0.0.1:5000/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
  
        if (!res.ok) {
          throw new Error("Server error");
        }
  
        const data = await res.json();
  
        // Expecting: { type: "phishing" | "safe", subtype?: "suspicious" }
        const type = data.type?.toUpperCase() || "UNKNOWN";
        const subtype = data.subtype ? ` (${data.subtype})` : "";
  
        resultDiv.textContent = `Result: ${type}${subtype}`;
  
        // Apply CSS class
        if (type === "PHISHING") {
          resultDiv.className = "result phishing";
        } else {
          resultDiv.className = "result safe";
        }
      });
    } catch (error) {
      resultDiv.textContent = "Backend not reachable";
      resultDiv.className = "result phishing";
    }
  });
  