
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
        renderMonthlyColumnChart();

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
               backgroundColor: "#36D9D0",
                pointBackgroundColor:"#E9A23B",
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

let monthlyColumnChart = null;

function renderMonthlyColumnChart() {
    const canvas = document.getElementById("monthlyColumnChart");
     console.log("CLUSTERED CHART FUNCTION STARTED");
    console.log("Column chart function called");
    console.log("Canvas:", canvas);
    console.log("Monthly KPI data:", monthlyKpiData?.length);
    console.log("Canvas found:", !!canvas);
console.log("Monthly data length:", monthlyKpiData?.length);

    if (!canvas || !monthlyKpiData || monthlyKpiData.length === 0) {
        return;
    }

    const labels = monthlyKpiData.map(row => row.month);

    if (monthlyColumnChart) {
        monthlyColumnChart.destroy();
    }
    console.log("Column chart data:", monthlyKpiData);
    console.log("Total requests:", monthlyKpiData.map(row => row.total_requests));
    console.log("Closed requests:", monthlyKpiData.map(row => row.closed_requests));

    monthlyColumnChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Total requests",
                    data: monthlyKpiData.map(row =>
                        Number(row.total_requests) || 0
                    ),
                    backgroundColor: "#B8DBD9",
                    borderColor: "#586F7C",
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: "Closed requests",
                    data: monthlyKpiData.map(row =>
                        Number(row.closed_requests) || 0
                    ),
                    backgroundColor: "#586F7C",
                    borderColor: "#40545F",
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: "top"
                },
                tooltip: {
                    enabled: true
                }
            },
            scales: {
                x: {
                    stacked: false,
                    ticks: {
                        maxTicksLimit: 12,
                        maxRotation: 45,
                        minRotation: 0
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "Number of requests"
                    }
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
