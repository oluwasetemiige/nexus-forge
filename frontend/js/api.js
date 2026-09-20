/* ==========================================================================
   Nexus Forge — API client
   Talks to the Flask backend at API_BASE. Handles auth token + errors.
   ========================================================================== */

const API_BASE = "http://localhost:5000/api/";

const Auth = {
  getToken() {
    return localStorage.getItem("nf_token");
  },
  setToken(token) {
    localStorage.setItem("nf_token", token);
  },
  clearToken() {
    localStorage.removeItem("nf_token");
    localStorage.removeItem("nf_user");
  },
  getUser() {
    const raw = localStorage.getItem("nf_user");
    return raw ? JSON.parse(raw) : null;
  },
  setUser(user) {
    localStorage.setItem("nf_user", JSON.stringify(user));
  },
  isLoggedIn() {
    return !!this.getToken();
  },
  logout() {
    this.clearToken();
    window.location.href = "index.html";
  },
  sendMessage:  (payload) => apiRequest("/messages",{
    method: "POST",
    body: payload,
    auth: true
  }),
  getMessages: (gigId, userId)=> apiRequest(`/messages/${gigId}/${userId}`,{
    auth: true
  }),

};

async function apiRequest(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = Auth.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path.replace(/^\/+/, "")}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw new Error(
      "Can't reach the Nexus Forge server. Make sure the Flask backend is running on port 5000."
    );
  }

  let data = {}; 
  try {
    data = await response.json();
  } catch (_e) {
    // no JSON body
  }

  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

const Api = {
  register: (payload) => apiRequest("/register", { method: "POST", body: payload }),
  login: (payload) => apiRequest("/login", { method: "POST", body: payload }),
  logout: () => apiRequest("/logout", { method: "POST", auth: true }),
  me: () => apiRequest("/me", { auth: true }),

  listGigs: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/gigs${qs ? `?${qs}` : ""}`);
  },
  getGig: (id) => apiRequest(`/gigs/${id}`),
  createGig: (payload) => apiRequest("/gigs", { method: "POST", body: payload, auth: true }),
  applyToGig: (id, payload) => apiRequest(`/gigs/${id}/apply`, { method: "POST", body: payload, auth: true }),
  updateApplicationStatus: (id, status) =>
    apiRequest(`/applications/${id}/status`, { method: "PUT", body: { status }, auth: true }),

  dashboard: () => apiRequest("/dashboard", { auth: true }),

  sendMessage:(payload)=>apiRequest("messages",{method: "POST", body: payload, auth: true}),
  getMessages: (gigId, userId)=> apiRequest(`/messages/${gigId}/${userId}`,
    {auth: true}),
};

/* ---------- Toast helper (shared UI feedback) ---------- */
function showToast(message, type = "success") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString + "Z").getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(isoString + "Z").toLocaleDateString();
}
