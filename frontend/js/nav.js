/* ==========================================================================
   Nexus Forge — Shared navbar logic
   Include after api.js on every page. Expects a <div id="nav-root"></div>
   ========================================================================== */

function renderNav(activePage = "") {
  const root = document.getElementById("nav-root");
  if (!root) return;

  const user = Auth.getUser();
  const loggedIn = Auth.isLoggedIn() && user;

  const linkClass = (page) => `${activePage === page ? "active" : ""}`;

  root.innerHTML = `
    <nav class="navbar">
      <div class="container nav-inner">
        <a href="index.html" class="logo">
          <span class="logo-mark"></span> Nexus Forge
        </a>
        <button class="nav-toggle" id="navToggle" aria-label="Toggle menu">☰</button>
        <div class="nav-links" id="navLinks">
          <a href="index.html" class="${linkClass('home')}">Home</a>
          <a href="browse.html" class="${linkClass('browse')}">Browse Gigs</a>
          ${loggedIn ? `<a href="dashboard.html" class="${linkClass('dashboard')}">Dashboard</a>` : ""}
          ${loggedIn && user.role === "client" ? `<a href="post-gig.html" class="${linkClass('post-gig')}">Post a Gig</a>` : ""}
          ${loggedIn ? `<a href="profile.html" class="${linkClass('profile')}">Profile</a>` : ""}

        </div>
        <div class="nav-actions">
          ${
            loggedIn
              ? `<span class="muted" style="font-size:0.85rem;">Hi, ${escapeHtml(user.name.split(" ")[0])}</span>
              <a href ="message.html" class="nav-message-icon" title ="Messages" arial-label="Open messages" style="display: inline-fles;align-items: center; justify-content:center;width:38px;height:38px;border-radius:50%;color:inherit;text-decoration:none;">
              <svg xmins="http://www.w3.org/2000/svg" width="21" height="21" viewBox = "0 0 24 24" fill ="none" stroke="CurrentColor" stroke-width ="1.8" stroke-linecap ="round" stroke-linejoin ="round">
              <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8
                          8.5 8.5 0 0 1-7.6 4.7
                          8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7
                          a8.4 8.4 0 0 1-.9-3.8
                          A8.5 8.5 0 0 1 8.7 3.9
                          a8.4 8.4 0 0 1 3.8-.9h.5
                          a8.5 8.5 0 0 1 8 8v.5z"/>
                </svg>
                </a>
                 <button class="btn btn-ghost btn-sm" id="navLogout">Log out</button>`
              : `<a href="login.html" class="btn btn-ghost btn-sm">Log in</a>
                 <a href="signup.html" class="btn btn-primary btn-sm">Sign up</a>`
          }
        </div>
      </div>
    </nav>
  `;

  document.getElementById("navToggle")?.addEventListener("click", () => {
    document.getElementById("navLinks").classList.toggle("open");
  });

  document.getElementById("navLogout")?.addEventListener("click", async () => {
    try {
      await Api.logout();
    } catch (_e) {
      // ignore — clear locally regardless
    }
    Auth.logout();
  });
}

function requireLogin() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}
