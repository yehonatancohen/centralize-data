// Persons list page logic

var currentPage = 1;
var perPage = 50;
var selectedIds = new Set();

function getDisplayName(p) {
    if (p.first_name || p.last_name) {
        return [(p.first_name || ""), (p.last_name || "")].filter(Boolean).join(" ");
    }
    return p.full_name || p.display_name || "-";
}

function getScoreClass(score) {
    if (score >= 60) return "score-high";
    if (score >= 30) return "score-medium";
    return "score-low";
}

function showToast(message, type) {
    type = type || "success";
    var toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

// ===== Load Persons =====

async function loadPersons() {
    var search = document.getElementById("search-input").value;
    var segment = document.getElementById("segment-filter").value;

    var params = new URLSearchParams({
        q: search,
        segment: segment,
        page: currentPage,
        per_page: perPage,
    });

    // Advanced filters
    var cityEl = document.getElementById("filter-city");
    var genderEl = document.getElementById("filter-gender");
    var minEventsEl = document.getElementById("filter-min-events");
    var minScoreEl = document.getElementById("filter-min-score");
    var maxScoreEl = document.getElementById("filter-max-score");
    var contactEl = document.getElementById("filter-contact");

    if (cityEl && cityEl.value) params.set("city", cityEl.value);
    if (genderEl && genderEl.value) params.set("gender", genderEl.value);
    if (minEventsEl && minEventsEl.value) params.set("min_events", minEventsEl.value);
    if (minScoreEl && minScoreEl.value) params.set("min_score", minScoreEl.value);
    if (maxScoreEl && maxScoreEl.value) params.set("max_score", maxScoreEl.value);
    if (contactEl && contactEl.value) {
        var c = contactEl.value;
        if (c === "has_phone") params.set("has_phone", "true");
        else if (c === "no_phone") params.set("has_phone", "false");
        else if (c === "has_email") params.set("has_email", "true");
        else if (c === "no_email") params.set("has_email", "false");
        else if (c === "has_instagram") params.set("has_instagram", "true");
        else if (c === "no_instagram") params.set("has_instagram", "false");
    }

    var res = await fetch("/api/persons?" + params);
    var data = await res.json();

    var tbody = document.querySelector("#persons-table tbody");
    tbody.innerHTML = "";

    if (!data.persons || data.persons.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state">' +
            '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' +
            '<p>No people found. Upload a file to get started.</p>' +
            '</td></tr>';
        updateBulkBar();
        return;
    }

    data.persons.forEach(function(p) {
        var tr = document.createElement("tr");
        tr.style.cursor = "pointer";
        var isSelected = selectedIds.has(p.id);
        var displayName = getDisplayName(p);

        // Build social links HTML
        var linksHtml = "";
        if (p.phone) {
            var waPhone = p.phone;
            if (waPhone.startsWith("0")) waPhone = "972" + waPhone.substring(1);
            linksHtml += '<a href="https://wa.me/' + waPhone + '" target="_blank" rel="noopener" title="WhatsApp" class="social-link wa-link">' +
                '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>' +
                '</a>';
        }
        if (p.instagram) {
            linksHtml += '<a href="https://instagram.com/' + p.instagram + '" target="_blank" rel="noopener" title="@' + p.instagram + '" class="social-link ig-link">' +
                '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="5"/><circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" stroke="none"/></svg>' +
                '</a>';
        }

        // Build checkbox cell with DOM (no inline handler)
        var cbTd = document.createElement("td");
        cbTd.style.textAlign = "center";
        var cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "row-cb";
        cb.dataset.id = p.id;
        cb.checked = isSelected;
        cb.addEventListener("change", function() {
            if (this.checked) selectedIds.add(p.id);
            else selectedIds.delete(p.id);
            updateBulkBar();
        });
        cb.addEventListener("click", function(e) { e.stopPropagation(); });
        cbTd.appendChild(cb);

        // Name cell
        var nameTd = document.createElement("td");
        nameTd.style.fontWeight = "500";
        var nameLink = document.createElement("a");
        nameLink.href = "/persons/" + p.id;
        nameLink.textContent = displayName;
        nameTd.appendChild(nameLink);

        // Links cell
        var linksTd = document.createElement("td");
        linksTd.className = "social-links";
        linksTd.innerHTML = linksHtml;
        linksTd.addEventListener("click", function(e) { e.stopPropagation(); });

        // Simple text cells
        var phoneTd = document.createElement("td");
        phoneTd.textContent = p.phone || "-";

        var emailTd = document.createElement("td");
        emailTd.textContent = p.email || "-";
        emailTd.style.color = "var(--text-secondary)";

        var igTd = document.createElement("td");
        igTd.textContent = p.instagram ? "@" + p.instagram : "-";
        igTd.style.color = "var(--text-secondary)";

        var eventsTd = document.createElement("td");
        eventsTd.textContent = p.events_attended || 0;

        var scoreTd = document.createElement("td");
        scoreTd.className = getScoreClass(p.total_score);
        scoreTd.textContent = p.total_score ? p.total_score.toFixed(1) : "0";

        var segTd = document.createElement("td");
        var badge = document.createElement("span");
        badge.className = "badge badge-" + p.segment;
        badge.textContent = p.segment;
        segTd.appendChild(badge);

        // Assemble row in column order
        tr.appendChild(cbTd);
        tr.appendChild(nameTd);
        tr.appendChild(phoneTd);
        tr.appendChild(emailTd);
        tr.appendChild(igTd);
        tr.appendChild(eventsTd);
        tr.appendChild(scoreTd);
        tr.appendChild(segTd);
        tr.appendChild(linksTd);

        // Row click navigates (skip if clicking checkbox or link)
        tr.addEventListener("click", function(e) {
            if (e.target.tagName === "INPUT" || e.target.tagName === "A" || e.target.closest("a")) return;
            window.location.href = "/persons/" + p.id;
        });

        tbody.appendChild(tr);
    });

    // Reset header checkbox
    document.getElementById("select-all-cb").checked = false;

    // Update export link
    var exportParams = new URLSearchParams();
    if (search) exportParams.set("search", search);
    if (segment) exportParams.set("segment", segment);
    document.getElementById("export-btn").href = "/api/export?" + exportParams;

    renderPagination(data.total);
    updateBulkBar();
}

// ===== Selection / Bulk =====

function updateBulkBar() {
    var bar = document.getElementById("bulk-bar");
    var count = selectedIds.size;
    if (count > 0) {
        bar.classList.remove("hidden");
        document.getElementById("selected-count").textContent = count + " selected";
    } else {
        bar.classList.add("hidden");
    }
}

async function bulkDelete() {
    var count = selectedIds.size;
    if (!count) return;
    if (!confirm("Delete " + count + " people? This cannot be undone.")) return;

    var res = await fetch("/api/persons/bulk-delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: Array.from(selectedIds) }),
    });
    var result = await res.json();
    if (result.success) {
        showToast("Deleted " + result.deleted + " people");
        selectedIds.clear();
        loadPersons();
    } else {
        showToast("Error: " + (result.error || "Unknown"), "error");
    }
}

async function bulkUpdate() {
    var count = selectedIds.size;
    if (!count) return;
    var field = document.getElementById("bulk-field").value;
    var value = document.getElementById("bulk-value").value;
    if (!field) { showToast("Select a field to update", "error"); return; }

    var res = await fetch("/api/persons/bulk-update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: Array.from(selectedIds), field: field, value: value }),
    });
    var result = await res.json();
    if (result.success) {
        showToast("Updated " + result.updated + " people");
        document.getElementById("bulk-field").value = "";
        document.getElementById("bulk-value").value = "";
        loadPersons();
    } else {
        showToast("Error: " + (result.error || "Unknown"), "error");
    }
}

// ===== Advanced Filters =====

function toggleFilters() {
    document.getElementById("advanced-filters").classList.toggle("hidden");
}

function clearFilters() {
    document.getElementById("filter-city").value = "";
    document.getElementById("filter-gender").value = "";
    document.getElementById("filter-min-events").value = "";
    document.getElementById("filter-min-score").value = "";
    document.getElementById("filter-max-score").value = "";
    document.getElementById("filter-contact").value = "";
    currentPage = 1;
    loadPersons();
}

// ===== Pagination =====

function renderPagination(total) {
    var container = document.getElementById("pagination");
    container.innerHTML = "";
    var totalPages = Math.ceil(total / perPage);
    if (totalPages <= 1) return;

    if (currentPage > 1) {
        var prev = document.createElement("a");
        prev.href = "#";
        prev.textContent = "Previous";
        prev.addEventListener("click", function(e) { e.preventDefault(); currentPage--; loadPersons(); });
        container.appendChild(prev);
    }

    var span = document.createElement("span");
    span.textContent = "Page " + currentPage + " of " + totalPages;
    container.appendChild(span);

    if (currentPage < totalPages) {
        var next = document.createElement("a");
        next.href = "#";
        next.textContent = "Next";
        next.addEventListener("click", function(e) { e.preventDefault(); currentPage++; loadPersons(); });
        container.appendChild(next);
    }
}

// ===== Wire up all event listeners (no inline onclick) =====

// Select-all checkbox in table header
document.getElementById("select-all-cb").addEventListener("change", function() {
    var checked = this.checked;
    document.querySelectorAll(".row-cb").forEach(function(box) {
        box.checked = checked;
        var id = parseInt(box.dataset.id);
        if (checked) selectedIds.add(id);
        else selectedIds.delete(id);
    });
    updateBulkBar();
});

// Filters toggle button
document.getElementById("toggle-filters-btn").addEventListener("click", toggleFilters);
document.getElementById("clear-filters-btn").addEventListener("click", clearFilters);
document.getElementById("apply-filters-btn").addEventListener("click", function() {
    currentPage = 1;
    loadPersons();
});

// Bulk action buttons
document.getElementById("select-all-btn").addEventListener("click", function() {
    document.querySelectorAll(".row-cb").forEach(function(box) {
        box.checked = true;
        selectedIds.add(parseInt(box.dataset.id));
    });
    document.getElementById("select-all-cb").checked = true;
    updateBulkBar();
});
document.getElementById("clear-selection-btn").addEventListener("click", function() {
    selectedIds.clear();
    document.querySelectorAll(".row-cb").forEach(function(box) { box.checked = false; });
    document.getElementById("select-all-cb").checked = false;
    updateBulkBar();
});
document.getElementById("bulk-update-btn").addEventListener("click", bulkUpdate);
document.getElementById("bulk-delete-btn").addEventListener("click", bulkDelete);

// Search debounce
var searchTimeout;
document.getElementById("search-input").addEventListener("input", function() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(function() { currentPage = 1; loadPersons(); }, 300);
});

document.getElementById("segment-filter").addEventListener("change", function() {
    currentPage = 1;
    loadPersons();
});

// Initial load
loadPersons();
