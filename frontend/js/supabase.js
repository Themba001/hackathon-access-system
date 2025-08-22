// supabase.js (actually API helper now)

// Base URL for FastAPI backend
const API_BASE = "http://localhost:8000";

// --------------------------------------------------
// Token helpers
// --------------------------------------------------
function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearToken() {
  localStorage.removeItem("token");
}

// --------------------------------------------------
// API fetch wrapper (automatically adds JWT)
// --------------------------------------------------
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    Swal.fire("Unauthorized", "Please log in again.", "warning");
    clearToken();
    document.getElementById("logout-btn").click();
    return null;
  }

  return res.json();
}

// --------------------------------------------------
// Auth API functions
// --------------------------------------------------
async function signup(email, password) {
  const res = await fetch(`${API_BASE}/facilitators/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return res.json();
}

async function login(email, password) {
  const res = await fetch(`${API_BASE}/facilitators/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  if (res.ok && data.access_token) {
    setToken(data.access_token);
  }
  return { res, data };
}

function logout() {
  clearToken();
}
