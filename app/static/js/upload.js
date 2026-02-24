// Upload page logic

const CANONICAL_FIELDS = [
    { value: "", label: "-- Skip --" },
    { value: "full_name", label: "Full Name" },
    { value: "first_name", label: "First Name" },
    { value: "last_name", label: "Last Name" },
    { value: "phone", label: "Phone" },
    { value: "email", label: "Email" },
    { value: "instagram", label: "Instagram" },
    { value: "city", label: "City" },
    { value: "amount_paid", label: "Amount Paid" },
    { value: "ticket_type", label: "Ticket Type" },
    { value: "event_name", label: "Event Name" },
    { value: "notes", label: "Notes" },
];

let currentImportId = null;
let currentMapping = {};
let uploadData = null;

function setActiveStep(stepNum) {
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`step-ind-${i}`);
        el.classList.remove("active", "done");
        if (i < stepNum) el.classList.add("done");
        if (i === stepNum) el.classList.add("active");
    }
}

// Step 1: File upload
const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");

uploadArea.addEventListener("click", () => fileInput.click());
uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
});
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
    document.getElementById("upload-progress").style.display = "flex";
    uploadArea.style.display = "none";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, "error");
            document.getElementById("upload-progress").style.display = "none";
            uploadArea.style.display = "block";
            return;
        }

        uploadData = data;
        currentImportId = data.import_id;
        showMappingStep(data);
    } catch (err) {
        showToast("Upload failed: " + err.message, "error");
        document.getElementById("upload-progress").style.display = "none";
        uploadArea.style.display = "block";
    }
}

// Step 2: Column mapping
function showMappingStep(data) {
    document.getElementById("step-upload").style.display = "none";
    document.getElementById("step-mapping").style.display = "block";
    setActiveStep(2);

    document.getElementById("mapping-filename").textContent = data.filename;
    document.getElementById("mapping-rowcount").textContent = data.row_count;

    const tbody = document.getElementById("mapping-tbody");
    tbody.innerHTML = "";

    for (const col of data.columns) {
        const mapInfo = data.mapping[col] || { field: null, confidence: 0 };
        const tr = document.createElement("tr");

        // Source column
        const tdSource = document.createElement("td");
        tdSource.textContent = col;
        tdSource.style.fontWeight = "500";
        tr.appendChild(tdSource);

        // Sample data
        const tdSample = document.createElement("td");
        const samples = data.preview
            .map(row => row[col])
            .filter(v => v != null && v !== "")
            .slice(0, 3);
        tdSample.textContent = samples.join(", ");
        tdSample.style.maxWidth = "200px";
        tdSample.style.overflow = "hidden";
        tdSample.style.textOverflow = "ellipsis";
        tdSample.style.color = "var(--text-secondary)";
        tr.appendChild(tdSample);

        // Mapping select
        const tdMap = document.createElement("td");
        const select = document.createElement("select");
        select.dataset.sourceCol = col;
        for (const f of CANONICAL_FIELDS) {
            const opt = document.createElement("option");
            opt.value = f.value;
            opt.textContent = f.label;
            if (f.value === mapInfo.field) opt.selected = true;
            select.appendChild(opt);
        }
        select.addEventListener("change", () => {
            currentMapping[col] = select.value || null;
        });
        tdMap.appendChild(select);
        tr.appendChild(tdMap);

        // Confidence
        const tdConf = document.createElement("td");
        const confClass = mapInfo.confidence >= 90 ? "mapping-high" : "mapping-low";
        tdConf.innerHTML = `<span class="mapping-confidence ${confClass}">${mapInfo.confidence}%</span>`;
        tr.appendChild(tdConf);

        tbody.appendChild(tr);
        currentMapping[col] = mapInfo.field;
    }
}

// Confirm mapping
document.getElementById("btn-confirm-mapping").addEventListener("click", async () => {
    const btn = document.getElementById("btn-confirm-mapping");
    btn.setAttribute("aria-busy", "true");
    btn.disabled = true;

    const eventSelect = document.getElementById("event-select");
    const payload = {
        mapping: currentMapping,
        event_id: eventSelect.value ? parseInt(eventSelect.value) : null,
        event_name: document.getElementById("event-name").value || null,
        event_date: document.getElementById("event-date").value || null,
    };

    try {
        const res = await fetch(`/api/imports/${currentImportId}/mapping`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result = await res.json();

        if (result.review_needed > 0) {
            showReviewStep(result);
        } else {
            showDoneStep(result);
        }
    } catch (err) {
        showToast("Import failed: " + err.message, "error");
    } finally {
        btn.removeAttribute("aria-busy");
        btn.disabled = false;
    }
});

// Step 3: Review duplicates
async function showReviewStep(importResult) {
    document.getElementById("step-mapping").style.display = "none";
    document.getElementById("step-review").style.display = "block";
    setActiveStep(3);

    document.getElementById("review-summary").textContent =
        `${importResult.new_persons} new people created, ${importResult.merged_persons} merged automatically, ${importResult.review_needed} need your review.`;

    const res = await fetch(`/api/imports/${currentImportId}/review`);
    const data = await res.json();
    const container = document.getElementById("review-candidates");
    container.innerHTML = "";

    for (const candidate of data.candidates) {
        const card = document.createElement("div");
        card.className = "review-card";
        card.dataset.candidateId = candidate.id;

        const scorePercent = (candidate.match_score * 100).toFixed(0);
        card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <span class="match-score">${scorePercent}% match via ${candidate.match_field}</span>
                <div class="review-actions">
                    <label><input type="radio" name="decision-${candidate.id}" value="merge" checked> Merge</label>
                    <label><input type="radio" name="decision-${candidate.id}" value="skip"> Create New</label>
                </div>
            </div>
            <div class="comparison">
                <div>
                    <strong>Existing Person</strong><br><br>
                    Name: ${candidate.existing.full_name || "-"}<br>
                    Phone: ${candidate.existing.phone || "-"}<br>
                    Email: ${candidate.existing.email || "-"}<br>
                    Instagram: ${candidate.existing.instagram || "-"}
                </div>
                <div>
                    <strong>Incoming Data</strong><br><br>
                    Name: ${candidate.incoming.full_name || "-"}<br>
                    Phone: ${candidate.incoming.phone || "-"}<br>
                    Email: ${candidate.incoming.email || "-"}<br>
                    Instagram: ${candidate.incoming.instagram || "-"}
                </div>
            </div>
        `;
        container.appendChild(card);
    }
}

// Finalize review
document.getElementById("btn-finalize").addEventListener("click", async () => {
    const btn = document.getElementById("btn-finalize");
    btn.setAttribute("aria-busy", "true");

    const cards = document.querySelectorAll(".review-card");
    const decisions = [];
    for (const card of cards) {
        const id = parseInt(card.dataset.candidateId);
        const radio = card.querySelector(`input[name="decision-${id}"]:checked`);
        decisions.push({ candidate_id: id, action: radio ? radio.value : "skip" });
    }

    try {
        const res = await fetch(`/api/imports/${currentImportId}/review`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ decisions }),
        });
        const result = await res.json();
        showDoneStep({ ...result, new_persons: result.created, merged_persons: result.merged, review_needed: 0 });
    } catch (err) {
        showToast("Finalize failed: " + err.message, "error");
    } finally {
        btn.removeAttribute("aria-busy");
    }
});

// Step 4: Done
function showDoneStep(result) {
    document.getElementById("step-mapping").style.display = "none";
    document.getElementById("step-review").style.display = "none";
    document.getElementById("step-done").style.display = "block";
    setActiveStep(4);

    document.getElementById("done-summary").innerHTML = `
        <p><strong>${result.new_persons || 0}</strong> new people added</p>
        <p><strong>${result.merged_persons || 0}</strong> existing records updated</p>
    `;
}

// Toast helper
function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
