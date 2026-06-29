const PUBLIC_API_BASE_URL = "https://api.example.com";

function normalizedRoute() {
  const url = new URL(window.location.href);
  const routeFromQuery = url.searchParams.get("route");

  if (routeFromQuery) {
    return "/" + routeFromQuery.replace(/^\/+/, "");
  }

  return url.pathname;
}

function extractDeviceId() {
  const route = normalizedRoute();
  const segments = route.split("/").filter(Boolean);
  const deviceIndex = segments.indexOf("device");

  if (deviceIndex === -1 || !segments[deviceIndex + 1]) {
    return null;
  }

  return decodeURIComponent(segments[deviceIndex + 1]);
}

function renderDeviceLabel(deviceId) {
  const label = document.getElementById("device-label");

  if (!deviceId) {
    label.textContent = "No device id found in URL.";
    return;
  }

  label.textContent = "Controlling device: " + deviceId;
}

async function sendCommand() {
  const deviceId = extractDeviceId();
  const status = document.getElementById("status");

  if (!deviceId) {
    status.textContent = "Missing device id.";
    return;
  }

  const payload = {
    mode: document.getElementById("mode").value,
    color: document.getElementById("color").value.slice(1),
    brightness: Number(document.getElementById("brightness").value),
  };

  status.textContent = "Ready to send to " + PUBLIC_API_BASE_URL;

  try {
    const response = await fetch(
      PUBLIC_API_BASE_URL + "/api/devices/" + encodeURIComponent(deviceId) + "/commands",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      status.textContent = "Backend responded with " + response.status;
      return;
    }

    status.textContent = "Command sent.";
  } catch (error) {
    status.textContent = "Backend not configured yet.";
  }
}

function initialize() {
  const deviceId = extractDeviceId();
  renderDeviceLabel(deviceId);
  document.getElementById("send-button").addEventListener("click", sendCommand);
}

initialize();
