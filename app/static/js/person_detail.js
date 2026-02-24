// Person detail page logic

function formatDate(dateStr) {
    if (!dateStr) return "-";
    const parts = dateStr.split("-");
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dateStr;
}

const personId = document.getElementById("person-detail").dataset.personId;

async function loadPerson() {
    const res = await fetch(`/api/persons/${personId}`);
    const p = await res.json();

    if (p.error) {
        document.getElementById("page-title-name").textContent = "Person not found";
        return;
    }

    // Build display name: prefer first + last, fall back to full_name
    const name = p.display_name || p.full_name || "Unknown";
    document.getElementById("page-title-name").textContent = name;
    document.title = `${name} - PartyDB`;

    const segBadge = document.getElementById("person-segment");
    segBadge.textContent = p.segment;
    segBadge.className = `badge badge-${p.segment}`;

    // Social links in topbar
    if (p.phone) {
        let waPhone = p.phone;
        if (waPhone.startsWith("0")) waPhone = "972" + waPhone.substring(1);
        const waEl = document.getElementById("wa-link");
        waEl.href = `https://wa.me/${waPhone}`;
        waEl.style.display = "inline-flex";
    }
    if (p.instagram) {
        const igEl = document.getElementById("ig-link");
        igEl.href = `https://instagram.com/${p.instagram}`;
        igEl.style.display = "inline-flex";
    }

    document.getElementById("score-total").textContent = p.total_score?.toFixed(1) || "0";
    document.getElementById("score-events").textContent = p.events_attended || "0";
    document.getElementById("score-spent").textContent = p.total_spent || "0";
    document.getElementById("score-days").textContent = p.days_since_last ?? "-";

    document.getElementById("person-phone").textContent = p.phone || "-";
    document.getElementById("person-email").textContent = p.email || "-";
    document.getElementById("person-instagram").textContent = p.instagram ? `@${p.instagram}` : "-";
    document.getElementById("person-city").textContent = p.city || "-";
    document.getElementById("person-dob").textContent = p.date_of_birth || "-";
    document.getElementById("person-age").textContent = p.age != null ? p.age : "-";
    document.getElementById("person-gender").textContent = p.gender ? p.gender.charAt(0).toUpperCase() + p.gender.slice(1) : "-";
    document.getElementById("person-notes").textContent = p.notes || "-";

    // Fill edit form
    document.getElementById("edit-name").value = p.full_name || "";
    document.getElementById("edit-phone").value = p.phone || "";
    document.getElementById("edit-email").value = p.email || "";
    document.getElementById("edit-instagram").value = p.instagram || "";
    document.getElementById("edit-city").value = p.city || "";
    document.getElementById("edit-dob").value = p.date_of_birth || "";
    document.getElementById("edit-gender").value = p.gender || "";
    document.getElementById("edit-notes").value = p.notes || "";

    // Attendance table
    const tbody = document.querySelector("#attendance-table tbody");
    tbody.innerHTML = "";

    if (p.attendance && p.attendance.length > 0) {
        for (const a of p.attendance) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-weight:500">${a.event_name || "-"}</td>
                <td>${formatDate(a.event_date)}</td>
                <td>${a.amount_paid || 0}</td>
                <td>${a.ticket_type || "-"}</td>
            `;
            tbody.appendChild(tr);
        }
    } else {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state"><p>No events attended yet</p></td></tr>`;
    }
}

// Toast helper
function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// Edit form
document.getElementById("edit-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        full_name: document.getElementById("edit-name").value || null,
        phone: document.getElementById("edit-phone").value || null,
        email: document.getElementById("edit-email").value || null,
        instagram: document.getElementById("edit-instagram").value || null,
        city: document.getElementById("edit-city").value || null,
        date_of_birth: document.getElementById("edit-dob").value || null,
        gender: document.getElementById("edit-gender").value || null,
        notes: document.getElementById("edit-notes").value || null,
    };

    const res = await fetch(`/api/persons/${personId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const result = await res.json();
    if (result.success) {
        showToast("Changes saved successfully!");
        loadPerson();
    } else {
        showToast("Error: " + (result.error || "Unknown error"), "error");
    }
});

// Delete
document.getElementById("btn-delete").addEventListener("click", async () => {
    if (!confirm("Are you sure you want to delete this person? This cannot be undone.")) return;

    const res = await fetch(`/api/persons/${personId}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
        window.location.href = "/persons";
    }
});

loadPerson();
