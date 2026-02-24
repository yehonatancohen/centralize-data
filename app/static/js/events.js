// Events page logic

// Format date from yyyy-mm-dd to dd/mm/yyyy
function formatDate(dateStr) {
    if (!dateStr) return "-";
    const parts = dateStr.split("-");
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateStr;
}

async function loadEvents() {
    const res = await fetch("/api/events");
    const data = await res.json();

    const tbody = document.querySelector("#events-table tbody");
    tbody.innerHTML = "";

    if (!data.events || data.events.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <p>No events yet. Create one to start tracking attendance.</p>
        </td></tr>`;
        return;
    }

    for (const e of data.events) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td style="font-weight:500">${e.name}</td>
            <td>${formatDate(e.event_date)}</td>
            <td style="color:var(--text-secondary)">${e.venue || "-"}</td>
            <td>${e.attendee_count || 0}</td>
            <td>
                <button onclick='editEvent(${e.id})' class="btn btn-ghost btn-sm">Edit</button>
                <a href="/api/export?event_id=${e.id}" class="btn btn-ghost btn-sm">Export</a>
                <button onclick="deleteEvent(${e.id})" class="btn btn-ghost btn-sm" style="color:var(--danger)">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

// Edit event
async function editEvent(id) {
    const res = await fetch(`/api/events/${id}`);
    const data = await res.json();
    if (data.error) return;

    const e = data.event;
    document.getElementById("edit-event-id").value = e.id;
    document.getElementById("edit-event-name").value = e.name || "";
    document.getElementById("edit-event-date").value = e.event_date || "";
    document.getElementById("edit-event-venue").value = e.venue || "";
    document.getElementById("edit-event-card").style.display = "block";
    document.getElementById("new-event-card").style.display = "none";
}

document.getElementById("edit-event-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const id = document.getElementById("edit-event-id").value;
    const body = {
        name: document.getElementById("edit-event-name").value,
        event_date: document.getElementById("edit-event-date").value || null,
        venue: document.getElementById("edit-event-venue").value || null,
    };

    const res = await fetch(`/api/events/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const result = await res.json();
    if (result.success) {
        document.getElementById("edit-event-card").style.display = "none";
        loadEvents();

        const toast = document.createElement("div");
        toast.className = "toast toast-success";
        toast.textContent = "Event updated!";
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
});

// Add event
document.getElementById("add-event-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        name: document.getElementById("new-event-name").value,
        event_date: document.getElementById("new-event-date").value || null,
        venue: document.getElementById("new-event-venue").value || null,
    };

    const res = await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const result = await res.json();
    if (result.id) {
        document.getElementById("new-event-name").value = "";
        document.getElementById("new-event-date").value = "";
        document.getElementById("new-event-venue").value = "";
        document.getElementById("new-event-card").style.display = "none";
        loadEvents();

        // Toast
        const toast = document.createElement("div");
        toast.className = "toast toast-success";
        toast.textContent = "Event created!";
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
});

async function deleteEvent(id) {
    if (!confirm("Delete this event and all its attendance records?")) return;
    await fetch(`/api/events/${id}`, { method: "DELETE" });
    loadEvents();
}

loadEvents();
