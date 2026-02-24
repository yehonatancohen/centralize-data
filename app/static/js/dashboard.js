// Dashboard page logic

let segmentsChart = null;

async function loadDashboard() {
    const [summaryRes, topRes, churnedRes] = await Promise.all([
        fetch("/api/dashboard/summary"),
        fetch("/api/dashboard/top-customers?limit=10"),
        fetch("/api/dashboard/churned"),
    ]);

    const summary = await summaryRes.json();
    const top = await topRes.json();
    const churned = await churnedRes.json();

    // Stats
    document.getElementById("total-persons").textContent = summary.total_persons;
    document.getElementById("total-events").textContent = summary.total_events;
    document.getElementById("total-imports").textContent = summary.total_imports;

    // Segments chart
    renderSegmentsChart(summary.segments);

    // Top customers table
    renderTable("top-customers-table", top.persons, [
        { key: "full_name", link: p => `/persons/${p.id}` },
        { key: "phone" },
        { key: "events_attended" },
        { key: "total_spent", format: v => v ? `${v}` : "0" },
        { key: "total_score", format: v => typeof v === "number" ? v.toFixed(1) : "0" },
        { key: "segment", format: v => `<span class="badge badge-${v}">${v}</span>` },
    ]);

    // Churned table
    renderTable("churned-table", churned.persons, [
        { key: "full_name", link: p => `/persons/${p.id}` },
        { key: "phone" },
        { key: "events_attended" },
        { key: "days_since_last" },
    ]);
}

function renderSegmentsChart(segments) {
    const ctx = document.getElementById("segments-chart").getContext("2d");

    const labels = ["VIP", "Regular", "New", "Churned", "Inactive", "Never Attended"];
    const data = [
        segments.vip || 0,
        segments.regular || 0,
        segments.new || 0,
        segments.churned || 0,
        segments.inactive || 0,
        segments.never || 0,
    ];
    const colors = ["#fbbf24", "#60a5fa", "#34d399", "#f87171", "#6b7280", "#4b5563"];

    if (segmentsChart) segmentsChart.destroy();
    segmentsChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 6,
            }],
        },
        options: {
            responsive: true,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#8b8fa3",
                        padding: 16,
                        font: { family: "Inter", size: 12 },
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    },
                },
            },
        },
    });
}

function renderTable(tableId, rows, columns) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = "";

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${columns.length}" class="empty-state"><p>No data yet</p></td></tr>`;
        return;
    }

    for (const row of rows) {
        const tr = document.createElement("tr");
        for (const col of columns) {
            const td = document.createElement("td");
            let value = row[col.key] ?? "-";
            if (col.format) value = col.format(value);
            if (col.link) {
                td.innerHTML = `<a href="${col.link(row)}">${value}</a>`;
            } else {
                td.innerHTML = value;
            }
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    }
}

loadDashboard();
