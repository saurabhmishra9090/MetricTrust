
let monthlyChart = null;
let monthlyKpiData = [];

const metricLabels = {
    closure_rate_pct: "Closure rate (%)",
    total_requests: "Total requests",
    closed_requests: "Closed requests",
    missing_closed_dates: "Missing closure dates"
};

async function loadMonthlyKpis() {
    const status = document.getElementById("chartStatus");

    try {
        status.textContent = "Loading monthly KPI data...";

        const response = await fetch("/api/monthly-kpis");

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();

        if (!Array.isArray(data) || data.length === 0) {
            throw new Error("No monthly KPI records are available.");
        }

        monthlyKpiData = data;
        renderMonthlyChart();

        status.textContent = `${data.length} monthly records loaded from MetricTrust database.`;
    } catch (error) {
        console.error("Monthly KPI chart error:", error);
        status.textContent = "Unable to load chart data. Check the Flask terminal.";
    }
}

function renderMonthlyChart() {
    const selector = document.getElementById("chartMetric");
    const selectedMetric = selector.value;

    const labels = monthlyKpiData.map(row => row.month);
    const values = monthlyKpiData.map(row => Number(row[selectedMetric]));

    const context = document.getElementById("monthlyKpiChart");

    if (monthlyChart) {
        monthlyChart.destroy();
    }

    monthlyChart = new Chart(context, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: metricLabels[selectedMetric],
                data: values,
                borderColor: "#586F7C",
                backgroundColor: "rgba(184, 219, 217, 0.35)",
                pointBackgroundColor: "#04724D",
                pointRadius: 3,
                pointHoverRadius: 6,
                borderWidth: 2,
                fill: true,
                tension: 0.25
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: "index"
            },
            plugins: {
                legend: {
                    display: true
                },
                tooltip: {
                    enabled: true
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 12,
                        maxRotation: 45
                    }
                },
                y: {
                    beginAtZero: selectedMetric !== "closure_rate_pct"
                }
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("chartMetric")
        .addEventListener("change", renderMonthlyChart);

    loadMonthlyKpis();
});

document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            const targetId = link.getAttribute("href");

            if (!targetId || !targetId.startsWith("#")) return;

            const target = document.querySelector(targetId);
            console.log("Navigation clicked:", targetId);
            console.log("Target found:", Boolean(target));  

            // Abhi section exist nahi karta toh page ko break mat karo.
            if (!target) {
                event.preventDefault();
                console.info(`Section ${targetId} will be added later.`);
                return;
            }

            navLinks.forEach((item) => {
                item.classList.remove("active");
            });

            link.classList.add("active");

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        });
    });
});
