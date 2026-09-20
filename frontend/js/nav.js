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
          ${loggedIn ? `<a href="message.html" class="${linkClass('message')}">message</a>` : ""}
        </div>
        <div class="nav-actions">
          ${
            loggedIn
              ? `<span class="muted" style="font-size:0.85rem;">Hi, ${escapeHtml(user.name.split(" ")[0])}</span>
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
