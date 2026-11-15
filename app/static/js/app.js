
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
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers
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
    await loadWaitlist();
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
        · ${Number(category.available ?? category.quantity ?? 0)} left
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
                ${
                  String(booking.status).toLowerCase() === "cancelled"
                    ? `· Refund ${money(booking.refund_amount)}`
                    : ""
                }
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
   await loadWaitlist();

  } catch (error) {
    showToast(error.message, "error");
  }
}


async function loadWaitlist() {
  const container = $("#myWaitlistList");
  if (!container) return;

  try {
    const data = await api("/waitlist/my");
    const entries = data.waitlist || [];

    if (!entries.length) {
      container.innerHTML = `
        <div class="empty-events">
          <h3>No waitlist entries.</h3>
          <p>When an event is sold out, you can join its waitlist.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = entries.map(entry => {
      const status = String(entry.status || "").toLowerCase();
      const offered = status === "offered";

      return `
        <article class="booking-card">
          <div>
            <span class="booking-id">WAITLIST #${Number(entry.id)}</span>

            <h3>${escapeHTML(entry.event_title)}</h3>

            <p>
              Ticket: ${escapeHTML(entry.category_name)}
            </p>

            <p>
              Status:
              <strong>${escapeHTML(status.toUpperCase())}</strong>
            </p>

            ${
              offered
                ? `
                  <p class="form-hint">
                    Offer expires:
                    ${escapeHTML(dateText(entry.hold_until))}
                  </p>

                  <div class="form-actions">
                    <button
                      class="button button-primary"
                      data-waitlist-accept="${Number(entry.id)}"
                    >
                      Accept offer
                    </button>

                    <button
                      class="button button-outline"
                      data-waitlist-decline="${Number(entry.id)}"
                    >
                      Decline
                    </button>
                  </div>
                `
                : ""
            }
          </div>
        </article>
      `;
    }).join("");

    setStatus(
      $("#waitlistStatus"),
      "Waitlist information loaded.",
      "success"
    );

  } catch (error) {
    setStatus(
      $("#waitlistStatus"),
      error.message,
      "error"
    );
  }
}

$("#myWaitlistList")?.addEventListener("click", async event => {
  const accept = event.target.closest("[data-waitlist-accept]");
  const decline = event.target.closest("[data-waitlist-decline]");

  if (accept) {
    await acceptWaitlistOffer(
      Number(accept.dataset.waitlistAccept)
    );
  }

  if (decline) {
    await declineWaitlistOffer(
      Number(decline.dataset.waitlistDecline)
    );
  }
});

async function acceptWaitlistOffer(id) {
  if (!confirm("Accept this ticket offer and confirm your booking?")) {
    return;
  }

  try {
    const result = await api(
      `/waitlist/${id}/accept`,
      { method: "POST" }
    );

    showToast(result.message || "Waitlist offer accepted.");

    await loadWaitlist();
    await loadBookings();

  } catch (error) {
    showToast(error.message, "error");
    await loadWaitlist();
  }
}

async function declineWaitlistOffer(id) {
  if (!confirm("Are you sure you want to decline this ticket offer?")) {
    return;
  }

  try {
    const result = await api(
      `/waitlist/${id}/decline`,
      { method: "POST" }
    );

    showToast(result.message || "Offer declined.");

    await loadWaitlist();

  } catch (error) {
    showToast(error.message, "error");
    await loadWaitlist();
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

    const alternatives = (result.alternatives || []).map(alternative =>
      `${alternative.venue_name} · ${dateText(alternative.start_time)} · ${money(alternative.price)}`
    );
    setStatus(
      $("#hireStatus"),
      [
        result.message || `Request submitted. Status: ${result.status || "received"}.`,
        result.reason,
        ...alternatives.map(item => `Alternative: ${item}`)
      ].filter(Boolean).join(" "),
      result.status === "confirmed" ? "success" : ""
    );

    form.reset();

  } catch (error) {
    setStatus($("#hireStatus"), error.message, "error");
  }
});

async function loadHireVenues() {
  const select = $("#hireVenue");
  if (!select) return;

  try {
    const venues = await api("/hire/venues");
    select.innerHTML = '<option value="">Select a venue</option>' +
      venues.map(venue => `
        <option value="${Number(venue.id)}">
          ${escapeHTML(venue.name)} · ${escapeHTML(venue.location)}
          · capacity ${Number(venue.capacity)}
          · ${money(venue.hourly_rate)}/hour
        </option>
      `).join("");
  } catch (error) {
    select.innerHTML = '<option value="">Could not load venues</option>';
    setStatus($("#hireStatus"), error.message, "error");
  }
}

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
          <td>${escapeHTML(item.event)}</td>
          <td>${Number(item.tickets_sold || 0)}</td>
          <td>${money(item.revenue)}</td>
          <td>${Number(item.checkins || 0)}</td>
          <td>${Number(item.capacity || 0)}</td>
          <td>${Number(item.remaining_capacity ?? 0)}</td>
        </tr>
      `).join("") || `
        <tr><td colspan="6">No event data available.</td></tr>
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
          <small>Conversation: ${escapeHTML(log.conversation_id)}</small>
        </article>
      `).join("") || "<p>No agent messages recorded yet.</p>";
    }

    await loadAdminHires();

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

async function loadAdminHires() {
  const container = $("#adminHireList");
  if (!container) return;

  const hires = await api("/admin/hires");
  container.innerHTML = hires.map(hire => `
    <article class="log-row">
      <div>
        <strong>${escapeHTML(hire.purpose)}</strong>
        <span>${escapeHTML(hire.status)} · ${dateText(hire.start_time)} - ${dateText(hire.end_time)}</span>
      </div>
      <p>${Number(hire.guests)} guests · ${money(hire.price)}</p>
      ${
        hire.status === "pending_admin"
          ? `<div class="form-actions">
              <button class="button button-primary" data-hire-decision="approve" data-hire-id="${Number(hire.id)}">Approve</button>
              <button class="button button-outline" data-hire-decision="reject" data-hire-id="${Number(hire.id)}">Reject</button>
            </div>`
          : ""
      }
    </article>
  `).join("") || "<p>No venue hire requests.</p>";

  if (!container.dataset.decisionHandlerAttached) {
    container.addEventListener("click", async event => {
      const button = event.target.closest("[data-hire-decision]");
      if (!button) return;
      try {
        const params = new URLSearchParams({
          decision: button.dataset.hireDecision
        });
        await api(
          `/admin/hire/${button.dataset.hireId}/decision?${params}`,
          { method: "POST" }
        );
        await loadAdminHires();
      } catch (error) {
        setStatus($("#dashboardStatus"), error.message, "error");
      }
    });
    container.dataset.decisionHandlerAttached = "true";
  }
}

// =====================================================
// TICKET SCANNER
// =====================================================

async function validateScannedTicket(code, eventId) {
  if (!state.user || !["staff", "admin"].includes(state.user.role)) {
    setStatus(
      $("#scanResult"),
      "Staff or admin login is required.",
      "error"
    );
    return false;
  }

  if (!code || !eventId) {
    setStatus(
      $("#scanResult"),
      "Enter both the ticket code and event ID.",
      "error"
    );
    return false;
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

    const message = result.reason || result.message || JSON.stringify(result);

    const rejected =
      result?.success === false ||
      String(result?.result || "").toUpperCase() === "REJECTED" ||
      ["FAILURE", "REFUSE", "REJECTED", "INVALID"].includes(
        String(result?.status || result?.performative || "").toUpperCase()
      );

    setStatus(
      $("#scanResult"),
      message,
      rejected ? "error" : "success"
    );

    return !rejected;

  } catch (error) {
    setStatus($("#scanResult"), error.message, "error");
    return false;
  }
}

$("#scanForm")?.addEventListener("submit", async event => {
  event.preventDefault();
  const code = $("#ticketCode")?.value.trim();
  const eventId = $("#scanEventId")?.value;
  await validateScannedTicket(code, eventId);
});

let qrScanner = null;
let scannerBusy = false;
$("#startCameraScan")?.addEventListener("click", async () => {
  if (!$("#scanEventId")?.value) {
    setStatus($("#scanResult"), "Enter the event ID before starting the camera.", "error");
    return;
  }
  if (!window.Html5Qrcode) {
    setStatus($("#scanResult"), "The camera scanner could not be loaded. Use manual code entry.", "error");
    return;
  }

  try {
    qrScanner = new Html5Qrcode("qrReader");
    await qrScanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      async decodedText => {
        if (scannerBusy) return;
        scannerBusy = true;
        $("#ticketCode").value = decodedText;
        try {
          const admitted = await validateScannedTicket(
            decodedText,
            $("#scanEventId").value
          );
          if (admitted && qrScanner.isScanning) {
            await qrScanner.stop();
            $("#startCameraScan").disabled = false;
            $("#stopCameraScan").disabled = true;
          }
        } finally {
          scannerBusy = false;
        }
      }
    );
    $("#startCameraScan").disabled = true;
    $("#stopCameraScan").disabled = false;
  } catch (error) {
    setStatus($("#scanResult"), `Could not start camera: ${error.message}`, "error");
  }
});

$("#stopCameraScan")?.addEventListener("click", async () => {
  if (qrScanner?.isScanning) {
    await qrScanner.stop();
  }
  $("#startCameraScan").disabled = false;
  $("#stopCameraScan").disabled = true;
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
if ($("#hireVenue")) {
  loadHireVenues();
}

// Check authentication on every page.
refreshUser();
// =====================================================
// ADMIN EVENT AND VENUE MANAGEMENT
// =====================================================



async function loadAdminVenues() {
  const select = $("#eventVenue");
  const list = $("#adminVenueList");

  try {
    const venues = await api("/admin/venues");

    // Update the venue dropdown used when creating events
    if (select) {
      select.innerHTML = `
        <option value="">Select venue</option>
        ${venues.map(venue => `
          <option value="${venue.id}">
            ${escapeHTML(venue.name)} (${escapeHTML(venue.location)})
          </option>
        `).join("")}
      `;
    }

    // Display existing venues with editable details
    if (list) {
      list.innerHTML = venues.map(venue => `
        <form class="admin-management venue-edit-form"
              data-venue-id="${venue.id}">

          <h4>${escapeHTML(venue.name)}</h4>

          <input
            name="name"
            value="${escapeHTML(venue.name)}"
            placeholder="Venue name"
            required
          >

          <input
            name="location"
            value="${escapeHTML(venue.location)}"
            placeholder="Location"
            required
          >

          <input
            name="capacity"
            type="number"
            min="1"
            value="${Number(venue.capacity)}"
            placeholder="Capacity"
            required
          >

          <input
            name="hourly_rate"
            type="number"
            min="0"
            step="0.01"
            value="${Number(venue.hourly_rate)}"
            placeholder="Hourly rate"
            required
          >

          <textarea
            name="description"
            placeholder="Description"
          >${escapeHTML(venue.description || "")}</textarea>

          <input
            name="image"
            value="${escapeHTML(venue.image || "")}"
            placeholder="Image URL"
          >

          <label>
            <input
              name="private_hire"
              type="checkbox"
              ${venue.private_hire ? "checked" : ""}
            >
            Available for private hire
          </label>

          <button class="button button-primary" type="submit">
            Save changes
          </button>

        </form>
      `).join("");

      // Handle venue editing
      if (!list.dataset.editHandlerAttached) {
        list.addEventListener("submit", async event => {
          const form = event.target.closest(".venue-edit-form");

          if (!form) return;

          event.preventDefault();

          const venueId = form.dataset.venueId;

          try {
            const params = new URLSearchParams(new FormData(form));

            // Include false when the checkbox is unchecked
            params.set(
              "private_hire",
              form.elements.private_hire.checked ? "true" : "false"
            );

            const result = await api(
              `/admin/venue/${venueId}?${params.toString()}`,
              { method: "PUT" }
            );

            setStatus(
              $("#venueFormStatus"),
              result.message,
              "success"
            );

            await loadAdminVenues();

          } catch (error) {
            setStatus(
              $("#venueFormStatus"),
              error.message,
              "error"
            );
          }
        });

        list.dataset.editHandlerAttached = "true";
      }
    }

  } catch (error) {
    setStatus($("#venueFormStatus"), error.message, "error");
  }
}



async function loadAdminEvents() {
  const container = $("#adminEventList");
  if (!container) return;

  try {
    const [events, venues] = await Promise.all([
      api("/admin/events"),
      api("/admin/venues")
    ]);

    container.innerHTML = events.map(event => {
      const ticket = event.ticket_categories?.[0] || {};

      const venueOptions = venues.map(venue => `
        <option
          value="${Number(venue.id)}"
          ${Number(venue.id) === Number(event.venue_id) ? "selected" : ""}
        >
          ${escapeHTML(venue.name)}
        </option>
      `).join("");

      return `
        <article class="log-row admin-event-item">

          <strong>${escapeHTML(event.title)}</strong>
          <span>Status: ${escapeHTML(event.status)}</span>

          <details class="event-edit-details">
            <summary>Edit event details</summary>

            <form class="admin-management event-edit-form"
                  data-event-edit="${Number(event.id)}">

              <label>Event title</label>
              <input
                name="title"
                value="${escapeHTML(event.title)}"
                required
              >

              <label>Category</label>
              <input
                name="category"
                value="${escapeHTML(event.category)}"
                required
              >

              <label>Venue</label>
              <select name="venue_id" required>
                ${venueOptions}
              </select>

              <label>Start time</label>
              <input
                type="datetime-local"
                name="start_time"
                value="${escapeHTML(String(event.start_time || "").slice(0, 16))}"
                required
              >

              <label>End time</label>
              <input
                type="datetime-local"
                name="end_time"
                value="${escapeHTML(String(event.end_time || "").slice(0, 16))}"
                required
              >

              <label>Description</label>
              <textarea name="description">${escapeHTML(event.description || "")}</textarea>

              <hr>

              <h4>Ticket category</h4>

              <label>Ticket name</label>
              <input
                name="ticket_name"
                value="${escapeHTML(ticket.name || "")}"
                required
              >

              <label>Ticket price (LKR)</label>
              <input
                type="number"
                name="price"
                min="0"
                step="0.01"
                value="${Number(ticket.price || 0)}"
                required
              >

              <label>Total ticket quantity</label>
              <input
                type="number"
                name="quantity"
                min="1"
                value="${Number(ticket.quantity || 1)}"
                required
              >

              <button class="button button-primary" type="submit">
                Save event changes
              </button>

            </form>
          </details>

          <div class="form-actions">

            <button
              class="button button-outline"
              type="button"
              data-event-id="${Number(event.id)}"
              data-event-status="published"
            >Publish</button>

            <button
              class="button button-outline"
              type="button"
              data-event-id="${Number(event.id)}"
              data-event-status="draft"
            >Set draft</button>

            <button
              class="button button-outline"
              type="button"
              data-event-id="${Number(event.id)}"
              data-event-status="cancelled"
            >Cancel</button>

          </div>

        </article>
      `;
    }).join("") || "<p>No events created yet.</p>";

  } catch (error) {
    container.textContent = error.message;
  }
}

function setupAdminManagement() {
  const venueForm = $("#createVenueForm");
  const eventForm = $("#createEventForm");
  const eventList = $("#adminEventList");

  if (!venueForm || !eventForm) return;

  loadAdminVenues();
  loadAdminEvents();

  // Create venue
  venueForm.addEventListener("submit", async event => {
    event.preventDefault();

    try {
      const params = new URLSearchParams(new FormData(venueForm));

      params.set(
        "private_hire",
        venueForm.elements.private_hire?.checked ? "true" : "false"
      );

      const result = await api(`/admin/venue?${params}`, {
        method: "POST"
      });

      setStatus($("#venueFormStatus"), result.message, "success");

      venueForm.reset();

      await loadAdminVenues();
      await loadAdminEvents();

    } catch (error) {
      setStatus($("#venueFormStatus"), error.message, "error");
    }
  });

  // Create event
  eventForm.addEventListener("submit", async event => {
    event.preventDefault();

    try {
      const params = new URLSearchParams(new FormData(eventForm));

      const result = await api(`/admin/event?${params}`, {
        method: "POST"
      });

      setStatus(
        $("#eventFormStatus"),
        `${result.message}. Status: ${result.status}`,
        "success"
      );

      eventForm.reset();

      await loadAdminEvents();
      await loadDashboard();

    } catch (error) {
      setStatus($("#eventFormStatus"), error.message, "error");
    }
  });

  if (!eventList) return;

  // Save edited event
  eventList.addEventListener("submit", async event => {
    const form = event.target.closest(".event-edit-form");

    if (!form) return;

    event.preventDefault();

    try {
      const eventId = form.dataset.eventEdit;
      const params = new URLSearchParams(new FormData(form));

      const result = await api(
        `/admin/event/${eventId}?${params}`,
        { method: "PUT" }
      );

      setStatus(
        $("#eventFormStatus"),
        result.message || "Event updated successfully.",
        "success"
      );

      await loadAdminEvents();
      await loadDashboard();

    } catch (error) {
      setStatus($("#eventFormStatus"), error.message, "error");
    }
  });

  // Publish, draft or cancel event
  eventList.addEventListener("click", async event => {
    const button = event.target.closest("[data-event-status]");

    if (!button) return;

    try {
      const id = button.dataset.eventId;
      const status = button.dataset.eventStatus;

      const params = new URLSearchParams({ status });

      const result = await api(
        `/admin/event/${id}/status?${params}`,
        { method: "POST" }
      );

      setStatus(
        $("#eventFormStatus"),
        result.message,
        "success"
      );

      await loadAdminEvents();
      await loadDashboard();

    } catch (error) {
      setStatus($("#eventFormStatus"), error.message, "error");
    }
  });
}
async function loadAdminStaff() {
  const container = $("#adminStaffList");
  if (!container) return;

  try {
    const staff = await api("/admin/staff");

    if (!staff.length) {
      container.innerHTML = "<p>No staff accounts have been created yet.</p>";
      return;
    }

    container.innerHTML = staff.map(member => `
      <div class="admin-list-item">
        <div>
          <strong>${escapeHTML(member.name)}</strong>
          <p>${escapeHTML(member.email)}</p>
          <small>Role: ${escapeHTML(member.role)}</small>
        </div>
      </div>
    `).join("");
  } catch (error) {
    container.innerHTML = "<p>Could not load staff accounts.</p>";
  }
}

function setupStaffManagement() {
  const form = $("#createStaffForm");
  if (!form || form.dataset.handlerAttached) return;

  form.dataset.handlerAttached = "true";

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const status = $("#staffFormStatus");
    const formData = new FormData(form);

    const params = new URLSearchParams({
      name: formData.get("name").trim(),
      email: formData.get("email").trim(),
      password: formData.get("password")
    });

    try {
      const result = await api(`/admin/staff?${params}`, {
        method: "POST"
      });

      status.textContent = result.message || "Staff account created.";
      status.className = "status-message success";

      form.reset();
      await loadAdminStaff();

    } catch (error) {
      status.textContent = error.message || "Could not create staff account.";
      status.className = "status-message error";
    }
  });
}

setupStaffManagement();
loadAdminStaff();
setupAdminManagement();