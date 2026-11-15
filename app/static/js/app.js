
"use strict";

// =====================================================
// EVENTSPHERE - MAIN JAVASCRIPT
// Shared by all pages
// =====================================================

const $ = (selector) => document.querySelector(selector);

const state = {
  user: null,
  events: [],
  venues: []
};

// =====================================================
// HELPERS
// =====================================================

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function money(value) {
  return new Intl.NumberFormat("en-LK", {
    style: "currency",
    currency: "LKR",
    maximumFractionDigits: 2
  }).format(Number(value || 0));
}

function dateText(value) {
  if (!value) return "Date to be announced";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? escapeHTML(value)
    : date.toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short"
      });
}

function showToast(message, type = "success") {
  const toast = $("#toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = `toast visible ${type}`;

  clearTimeout(state.toastTimer);

  state.toastTimer = setTimeout(() => {
    toast.className = "toast";
  }, 3800);
}

function setStatus(element, message, type = "") {
  if (!element) return;

  element.textContent = message;
  element.className = `status-message ${type}`.trim();
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options
  });

  const contentType = response.headers.get("content-type") || "";

  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof data === "object"
      ? data.detail || data.message
      : data;

    throw new Error(detail || `Request failed (${response.status})`);
  }

  return data;
}

function formBody(form) {
  return new FormData(form);
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.hidden = false;
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.hidden = true;
}

// =====================================================
// AUTHENTICATION
// =====================================================

async function refreshUser() {
  try {
    const data = await api("/auth/me");
    state.user = data.user || data;
  } catch {
    state.user = null;
  }

  const loggedIn = Boolean(state.user);
  const role = state.user?.role;

  if ($("#navUser")) {
    $("#navUser").textContent = loggedIn
      ? (state.user.name || state.user.email || "User")
      : "Guest";
  }

  if ($("#authOpenBtn")) {
    $("#authOpenBtn").hidden = loggedIn;
  }

  if ($("#logoutBtn")) {
    $("#logoutBtn").hidden = !loggedIn;
  }

  if ($("#myBookingsNav")) {
    $("#myBookingsNav").hidden =
      !loggedIn || role !== "attendee";
  }

  if ($("#adminNav")) {
    $("#adminNav").hidden = role !== "admin";
  }

  if ($("#scannerNav")) {
    $("#scannerNav").hidden =
      !["admin", "staff"].includes(role);
  }

  if (loggedIn && role === "attendee" && $("#bookingsList")) {
    await loadBookings();
  }

  if (loggedIn && role === "admin" && $("#dashboardStats")) {
    await loadDashboard();
  }
}

// Open sign-in modal
$("#authOpenBtn")?.addEventListener("click", () => {
  openModal("authModal");
});

// Login form
$("#loginForm")?.addEventListener("submit", async event => {
  event.preventDefault();

  const form = event.currentTarget;
  const button = form.querySelector('[type="submit"]');

  if (button) button.disabled = true;

  setStatus($("#authStatus"), "Signing in...");

  try {
    await api("/auth/login", {
      method: "POST",
      body: formBody(form)
    });

    form.reset();
    closeModal("authModal");

    await refreshUser();

    showToast("Login successful!");

    // Refresh to load the correct page content and permissions.
    window.location.reload();

  } catch (error) {
    setStatus($("#authStatus"), error.message, "error");
  } finally {
    if (button) button.disabled = false;
  }
});

// Registration form
$("#registerForm")?.addEventListener("submit", async event => {
  event.preventDefault();

  const form = event.currentTarget;
  const email = form.elements.email.value;
  const button = form.querySelector('[type="submit"]');

  if (button) button.disabled = true;

  try {
    await api("/auth/register", {
      method: "POST",
      body: formBody(form)
    });

    form.reset();

    setStatus(
      $("#authStatus"),
      "Account created successfully. Please sign in.",
      "success"
    );

    document.querySelector('[data-auth-tab="login"]')?.click();

    const emailInput = $("#loginForm [name='email']");
    if (emailInput) emailInput.value = email;

  } catch (error) {
    setStatus($("#authStatus"), error.message, "error");
  } finally {
    if (button) button.disabled = false;
  }
});

// Login / register tabs
document.querySelectorAll("[data-auth-tab]").forEach(tab => {
  tab.addEventListener("click", () => {
    const register = tab.dataset.authTab === "register";

    document.querySelectorAll("[data-auth-tab]").forEach(item => {
      item.classList.toggle("active", item === tab);
    });

    if ($("#loginForm")) {
      $("#loginForm").hidden = register;
    }

    if ($("#registerForm")) {
      $("#registerForm").hidden = !register;
    }

    if ($("#authTitle")) {
      $("#authTitle").innerHTML = register
        ? 'Create your <span>account.</span>'
        : 'Your next experience <span>awaits.</span>';
    }

    setStatus($("#authStatus"), "");
  });
});

// Logout
$("#logoutBtn")?.addEventListener("click", async () => {
  try {
    await api("/auth/logout", {
      method: "POST"
    });

    state.user = null;
    showToast("You have signed out.");

    window.location.href = "/";

  } catch (error) {
    showToast(error.message, "error");
  }
});

// =====================================================
// MODALS
// =====================================================

document.querySelectorAll("[data-close]").forEach(button => {
  button.addEventListener("click", () => {
    closeModal(button.dataset.close);
  });
});

document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
  backdrop.addEventListener("click", event => {
    if (event.target === backdrop) {
      backdrop.hidden = true;
    }
  });
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    document.querySelectorAll(".modal-backdrop").forEach(modal => {
      modal.hidden = true;
    });
  }
});

// =====================================================
// MOBILE NAVIGATION
// =====================================================

$("#menuToggle")?.addEventListener("click", () => {
  const nav = $("#navLinks");
  if (!nav) return;

  const open = nav.classList.toggle("active");

  $("#menuToggle").setAttribute(
    "aria-expanded",
    String(open)
  );

  $("#menuToggle").textContent = open ? "×" : "☰";
});

$("#navLinks")?.addEventListener("click", event => {
  if (event.target.closest("a")) {
    $("#navLinks").classList.remove("active");

    $("#menuToggle")?.setAttribute(
      "aria-expanded",
      "false"
    );

    if ($("#menuToggle")) {
      $("#menuToggle").textContent = "☰";
    }
  }
});

// =====================================================
// EVENTS
// =====================================================

async function loadEvents() {
  if (!$("#eventsGrid")) return;

  setStatus($("#eventStatus"), "Loading published events...");

  const params = new URLSearchParams();

  const search = $("#eventSearch")?.value.trim() || "";
  const category = $("#eventCategory")?.value || "";

  if (search) params.set("search", search);
  if (category) params.set("category", category);

  try {
    const data = await api(
      `/events${params.size ? "?" + params.toString() : ""}`
    );

    state.events = Array.isArray(data)
      ? data
      : data.events || data.items || [];

    populateCategories();
    renderEvents();

    setStatus(
      $("#eventStatus"),
      `${state.events.length} event(s) found.`,
      "success"
    );

  } catch (error) {
    setStatus(
      $("#eventStatus"),
      `Could not load events: ${error.message}`,
      "error"
    );
  }
}

function populateCategories() {
  const select = $("#eventCategory");
  if (!select) return;

  const current = select.value;

  const categories = [
    ...new Set(
      state.events.map(event => event.category).filter(Boolean)
    )
  ].sort();

  select.innerHTML =
    '<option value="">All categories</option>' +
    categories.map(category => `
      <option value="${escapeHTML(category)}">
        ${escapeHTML(category)}
      </option>
    `).join("");

  if (categories.includes(current)) {
    select.value = current;
  }
}

function renderEvents() {
  const grid = $("#eventsGrid");
  if (!grid) return;

  if (!state.events.length) {
    grid.innerHTML = `
      <div class="empty-events">
        <div class="empty-icon">✦</div>
        <h3>No events found.</h3>
        <p>Try another search or check back later.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = state.events.map(event => {
    const categories =
      event.ticket_categories || event.categories || [];

    const venue =
      event.venue?.name ||
      event.venue_name ||
      "Venue details available";

    const id = Number(event.id);

    const options = categories.map(category => `
      <option value="${Number(category.id)}">
        ${escapeHTML(category.name || "General admission")}
        · ${money(category.price)}
      </option>
    `).join("");

    return `
      <article class="event-card">

        <div class="event-card-art">
          <span class="event-category">
            ${escapeHTML(event.category || "EVENT")}
          </span>
          <span class="event-card-mark">E</span>
        </div>

        <div class="event-card-body">

          <div class="event-meta">
            ${escapeHTML(dateText(event.start_time))}
          </div>

          <h3>${escapeHTML(event.title || "Untitled event")}</h3>

          <p class="event-description">
            ${escapeHTML(event.description || "Join us for this experience.")}
          </p>

          <div class="event-location">
            ⌖ ${escapeHTML(venue)}
          </div>

          ${
            categories.length
              ? `
                <label class="ticket-select">
                  <span>Ticket category</span>
                  <select id="category-${id}">
                    ${options}
                  </select>
                </label>
              `
              : `<p class="form-hint">No ticket categories available.</p>`
          }

          <div class="event-card-actions">

            <button
              class="button button-primary"
              data-book="${id}"
              ${!categories.length ? "disabled" : ""}
            >
              Book tickets
            </button>

            <button
              class="text-button"
              data-waitlist="${id}"
              ${!categories.length ? "disabled" : ""}
            >
              Join waitlist
            </button>

          </div>

        </div>
      </article>
    `;
  }).join("");
}

$("#eventSearchForm")?.addEventListener("submit", event => {
  event.preventDefault();
  loadEvents();
});

$("#eventCategory")?.addEventListener("change", loadEvents);

$("#eventsGrid")?.addEventListener("click", event => {
  const book = event.target.closest("[data-book]");
  const waitlist = event.target.closest("[data-waitlist]");

  if (book) {
    bookEvent(Number(book.dataset.book));
  }

  if (waitlist) {
    joinWaitlist(Number(waitlist.dataset.waitlist));
  }
});

// =====================================================
// BOOKING
// =====================================================

async function bookEvent(eventId) {
  if (!state.user) {
    openModal("authModal");
    return;
  }

  if (state.user.role !== "attendee") {
    showToast("Only attendees can book tickets.", "error");
    return;
  }

  const category = $(`#category-${eventId}`)?.value;

  if (!category) {
    showToast("Select a ticket category.", "error");
    return;
  }

  const quantity = prompt(
    "How many tickets? Maximum 6.",
    "1"
  );

  if (quantity === null) return;

  const count = Number(quantity);

  if (!Number.isInteger(count) || count < 1 || count > 6) {
    showToast("Enter a whole number between 1 and 6.", "error");
    return;
  }

  const params = new URLSearchParams({
    event_id: String(eventId),
    category_id: String(category),
    quantity: String(count)
  });

  try {
    const result = await api(
      `/booking/create?${params.toString()}`,
      { method: "POST" }
    );

    showToast(result.message || "Booking successful!");

    window.location.href = "/my-bookings";

  } catch (error) {
    showToast(error.message, "error");
  }
}

// =====================================================
// BOOKING HISTORY
// =====================================================

async function loadBookings() {
  if (!$("#bookingsList")) return;

  try {
    const data = await api("/booking/history");
    const bookings = data.bookings || [];

    if (!bookings.length) {
      $("#bookingsList").innerHTML = `
        <div class="empty-events">
          <h3>No bookings yet.</h3>
          <p>Your tickets will appear here after booking.</p>
          <a href="/events-page" class="button button-primary">
            Discover events
          </a>
        </div>
      `;
    } else {
      $("#bookingsList").innerHTML = bookings.map(booking => {
        const id = Number(booking.booking_id);
        const tickets = booking.tickets || [];

        return `
          <article class="booking-card">

            <div>
              <span class="booking-id">BOOKING #${id}</span>

              <h3>
                ${escapeHTML(
                  booking.event_title || `Event #${booking.event_id}`
                )}
              </h3>

              <p>
                ${Number(booking.quantity || tickets.length)} ticket(s)
                · ${money(booking.total)}
                · ${escapeHTML(booking.status || "unknown")}
              </p>

                ${tickets.map(ticket => `
                  <div class="ticket-row">
                    <h4>Ticket #${Number(ticket.ticket_id)}</h4>

                    <p>Status: ${escapeHTML(ticket.status)}</p>

                    ${
                      ticket.qr_code
                        ? `<img
                            src="${escapeHTML(ticket.qr_code)}"
                            alt="QR code for ticket ${Number(ticket.ticket_id)}"
                            style="width:180px;height:180px;object-fit:contain;"
                          >`
                        : "<p>QR code unavailable.</p>"
                    }

                    <p>Ticket code:</p>
                    <code style="word-break:break-all;">
                      ${escapeHTML(ticket.ticket_code)}
                    </code>
                  </div>
                `).join("")}
            </div>

            ${
              String(booking.status).toLowerCase() === "confirmed"
                ? `
                  <button
                    class="button button-outline"
                    data-cancel="${id}"
                  >
                    Cancel booking
                  </button>
                `
                : ""
            }

          </article>
        `;
      }).join("");
    }

    setStatus(
      $("#bookingStatus"),
      "Booking history loaded.",
      "success"
    );

  } catch (error) {
    setStatus($("#bookingStatus"), error.message, "error");
  }
}

$("#bookingsList")?.addEventListener("click", event => {
  const button = event.target.closest("[data-cancel]");

  if (button) {
    cancelBooking(Number(button.dataset.cancel));
  }
});

async function cancelBooking(id) {
  if (!confirm("Are you sure you want to cancel this booking?")) {
    return;
  }

  try {
    const result = await api(
      `/booking/${id}/cancel`,
      { method: "POST" }
    );

    showToast(result.message || "Booking cancelled.");

    await loadBookings();

  } catch (error) {
    showToast(error.message, "error");
  }
}

// =====================================================
// WAITLIST
// =====================================================

async function joinWaitlist(eventId) {
  if (!state.user) {
    openModal("authModal");
    return;
  }

  if (state.user.role !== "attendee") {
    showToast("Only attendees can join the waitlist.", "error");
    return;
  }

  const category = $(`#category-${eventId}`)?.value;

  if (!category) {
    showToast("Select a ticket category.", "error");
    return;
  }

  const body = new FormData();

  body.append("event_id", String(eventId));
  body.append("category_id", String(category));

  try {
    const result = await api("/waitlist/join", {
      method: "POST",
      body
    });

    showToast(result.message || "Joined the waitlist.");

  } catch (error) {
    showToast(error.message, "error");
  }
}

// =====================================================
// VENUE HIRE
// =====================================================

$("#hireForm")?.addEventListener("submit", async event => {
  event.preventDefault();

  if (!state.user) {
    openModal("authModal");
    return;
  }

  if (state.user.role !== "attendee") {
    setStatus(
      $("#hireStatus"),
      "Only attendees can request venue hire.",
      "error"
    );
    return;
  }

  const form = event.currentTarget;

  try {
    const result = await api("/hire/request", {
      method: "POST",
      body: formBody(form)
    });

    setStatus(
      $("#hireStatus"),
      result.message ||
        `Request submitted. Status: ${result.status || "received"}.`,
      "success"
    );

    form.reset();

  } catch (error) {
    setStatus($("#hireStatus"), error.message, "error");
  }
});

// =====================================================
// ADMIN DASHBOARD
// =====================================================

async function loadDashboard() {
  if (!$("#dashboardStats")) return;

  setStatus($("#dashboardStatus"), "Loading dashboard...");

  try {
    const data = await api("/dashboard/summary");
    const events = data.events || [];

    const sold = events.reduce(
      (sum, item) => sum + Number(item.tickets_sold || 0),
      0
    );

    const revenue = events.reduce(
      (sum, item) => sum + Number(item.revenue || 0),
      0
    );

    const checkins = events.reduce(
      (sum, item) => sum + Number(item.checkins || 0),
      0
    );

    $("#dashboardStats").innerHTML = [
      ["Tickets sold", sold],
      ["Revenue", money(revenue)],
      ["Check-ins", checkins],
      ["Events", events.length]
    ].map(([label, value]) => `
      <div class="stat-card">
        <span>${escapeHTML(label)}</span>
        <strong>${value}</strong>
      </div>
    `).join("");

    if ($("#dashboardEvents")) {
      $("#dashboardEvents").innerHTML = events.map(item => `
        <tr>
          <td>${escapeHTML(item.title)}</td>
          <td>${Number(item.tickets_sold || 0)}</td>
          <td>${money(item.revenue)}</td>
          <td>${Number(item.checkins || 0)}</td>
          <td>${Number(item.remaining_capacity ?? 0)}</td>
        </tr>
      `).join("") || `
        <tr><td colspan="5">No event data available.</td></tr>
      `;
    }

    if ($("#agentLogs")) {
      $("#agentLogs").innerHTML = (data.agent_logs || []).map(log => `
        <article class="log-row">
          <div>
            <strong>
              ${escapeHTML(log.sender)} → ${escapeHTML(log.receiver)}
            </strong>
            <span>
              ${escapeHTML(log.performative)}
              · ${escapeHTML(dateText(log.created_at))}
            </span>
          </div>
          <code>
            ${escapeHTML(
              typeof log.content === "string"
                ? log.content
                : JSON.stringify(log.content || {})
            )}
          </code>
        </article>
      `).join("") || "<p>No agent messages recorded yet.</p>";
    }

    setStatus(
      $("#dashboardStatus"),
      "Dashboard refreshed successfully.",
      "success"
    );

  } catch (error) {
    setStatus($("#dashboardStatus"), error.message, "error");
  }
}

$("#refreshDashboardBtn")?.addEventListener("click", loadDashboard);

// =====================================================
// TICKET SCANNER
// =====================================================

$("#scanForm")?.addEventListener("submit", async event => {
  event.preventDefault();

  if (!state.user || !["staff", "admin"].includes(state.user.role)) {
    setStatus(
      $("#scanResult"),
      "Staff or admin login is required.",
      "error"
    );
    return;
  }

  const form = event.currentTarget;

  const code = $("#ticketCode")?.value.trim();
  const eventId = $("#scanEventId")?.value;

  if (!code || !eventId) {
    setStatus(
      $("#scanResult"),
      "Enter both the ticket code and event ID.",
      "error"
    );
    return;
  }

  const params = new URLSearchParams({
    code,
    event_id: eventId
  });

  try {
    const result = await api(
      `/scanner/check?${params.toString()}`,
      { method: "POST" }
    );

    const message = typeof result === "string"
      ? result
      : result.message || JSON.stringify(result);

    const rejected =
      result?.success === false ||
      ["FAILURE", "REFUSE", "REJECTED", "INVALID"].includes(
        String(result?.status || result?.performative || "").toUpperCase()
      );

    setStatus(
      $("#scanResult"),
      message,
      rejected ? "error" : "success"
    );

    if (!rejected) form.reset();

  } catch (error) {
    setStatus($("#scanResult"), error.message, "error");
  }
});

// =====================================================
// PAGE INITIALIZATION
// =====================================================

if ($("#currentYear")) {
  $("#currentYear").textContent = new Date().getFullYear();
}

// Load events only on the events page.
if ($("#eventsGrid")) {
  loadEvents();
}

// Check authentication on every page.
refreshUser();
