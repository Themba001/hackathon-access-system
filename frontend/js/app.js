// app.js

// -------------------------------
// Config
// -------------------------------
const API_URL = "https://hackathon-access-system.onrender.com";

// -------------------------------
// Auth helpers
// -------------------------------
function saveToken(token) {
  localStorage.setItem("access_token", token);
}
function getToken() {
  return localStorage.getItem("access_token");
}
function clearToken() {
  localStorage.removeItem("access_token");
}

// -------------------------------
// API wrappers
// -------------------------------
async function signup(email, password) {
  const res = await fetch(`${API_URL}/facilitators/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return res.json();
}

async function login(email, password) {
  const res = await fetch(`${API_URL}/facilitators/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  return { res, data };
}

async function apiFetch(path, method = "GET", body = null) {
  const token = getToken();
  const options = {
    method,
    headers: { Authorization: "Bearer " + token },
  };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(API_URL + path, options);
  return res.json();
}

// -------------------------------
// Section control
// -------------------------------
function showApp() {
  document.getElementById("login-section").style.display = "none";
  document.getElementById("app-section").style.display = "block";
  document.getElementById("logout-btn").style.display = "inline-block";
}

function showLogin() {
  document.getElementById("login-section").style.display = "flex";
  document.getElementById("app-section").style.display = "none";
  document.getElementById("logout-btn").style.display = "none";
}

// -------------------------------
// Event Listeners
// -------------------------------

// Login
document.getElementById("login-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const { res, data } = await login(email, password);
    if (res.ok && data.access_token) {
      saveToken(data.access_token);
      Swal.fire("Welcome!", "Login successful", "success");
      showApp();
    } else {
      Swal.fire("Error", data.detail || "Login failed", "error");
    }
  } catch (err) {
    Swal.fire("Error", err.message, "error");
  }
});

// Signup
document.getElementById("signup-link")?.addEventListener("click", async (e) => {
  e.preventDefault();
  const { value: formValues } = await Swal.fire({
    title: "Sign Up",
    html: `
      <input type="email" id="swal-email" class="swal2-input" placeholder="Email">
      <input type="password" id="swal-password" class="swal2-input" placeholder="Password">
    `,
    focusConfirm: false,
    preConfirm: () => ({
      email: document.getElementById("swal-email").value,
      password: document.getElementById("swal-password").value,
    }),
  });

  if (formValues) {
    try {
      const data = await signup(formValues.email, formValues.password);
      if (data.message) {
        Swal.fire("Success", data.message, "success");
      } else {
        Swal.fire("Error", data.detail || "Signup failed", "error");
      }
    } catch (err) {
      Swal.fire("Error", err.message, "error");
    }
  }
});

// Logout
document.getElementById("logout-btn")?.addEventListener("click", () => {
  clearToken();
  Swal.fire("Logged out", "You have been logged out.", "info");
  showLogin();
});

// Sidebar toggle
const sidebar = document.getElementById("sidebar");
const menuToggle = document.getElementById("menu-toggle");
const sidebarClose = document.getElementById("sidebar-close");

menuToggle?.addEventListener("click", () => sidebar.classList.toggle("active"));
sidebarClose?.addEventListener("click", () => sidebar.classList.remove("active"));

// Sidebar navigation
document.querySelectorAll(".sidebar a").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const page = link.dataset.page;
    document.getElementById("page-content").innerHTML = "";

    if (page === "bus") renderScannerPage("Bus Boarding", "/boarding");
    else if (page === "registration") renderScannerPage("Check-In", "/checkin");
    else if (page === "meals") renderScannerPage("Meal Collection", "/meals");
    else document.getElementById("page-content").innerHTML =
      `<h2>${page}</h2><p>Loading content...</p>`;

    sidebar.classList.remove("active");
  });
});

// Close sidebar on outside click
document.addEventListener("click", (e) => {
  if (sidebar.classList.contains("active") && !sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
    sidebar.classList.remove("active");
  }
});

// -------------------------------
// QR Scanner
// -------------------------------
let html5QrcodeScanner;

function renderScannerPage(title, endpoint) {
  document.getElementById("page-content").innerHTML = `
    <h2>${title}</h2>
    <div id="qr-reader" style="width:300px;"></div>
    <p id="scan-result" style="margin-top:10px; font-weight:bold;"></p>
  `;
  startScanner(endpoint);
}

function startScanner(endpoint) {
  const qrRegionId = "qr-reader";

  if (html5QrcodeScanner) {
    html5QrcodeScanner.clear();
  }

  html5QrcodeScanner = new Html5Qrcode(qrRegionId);

  html5QrcodeScanner
    .start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      async (decodedText) => {
        document.getElementById("scan-result").textContent =
          "Scanned: " + decodedText;

        try {
          // Parse QR: "name|email|participant_type|event_code"
          const parts = decodedText.split("|");
          if (parts.length < 2) throw new Error("Invalid QR format");
          const email = parts[1].trim();

          // Get participant_id from backend
          const token = getToken();
          const idRes = await fetch(`${API_URL}/participant-id?email=${encodeURIComponent(email)}`, {
            headers: { Authorization: "Bearer " + token },
          });

          if (!idRes.ok) {
            const errData = await idRes.json();
            throw new Error(errData.detail || "Participant not found");
          }

          const { participant_id } = await idRes.json();

          // Send to the intended action endpoint
          const res = await fetch(`${API_URL}${endpoint}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer " + token,
            },
            body: JSON.stringify({ participant_id, qr_data: decodedText }),
          });

          const data = await res.json();

          if (res.ok) {
            Swal.fire("Success ✅", data.message || "Action completed", "success");
          } else {
            Swal.fire("Error", data.detail || "Action failed", "error");
          }
        } catch (err) {
          Swal.fire("Error", err.message, "error");
        }

        html5QrcodeScanner.stop();
      },
      (errorMessage) => {
        // ignore scan errors
      }
    )
    .catch((err) => {
      Swal.fire("Error", "Camera start failed: " + err, "error");
    });
}


// -------------------------------
// Init
// -------------------------------
if (getToken()) showApp();
else showLogin();
