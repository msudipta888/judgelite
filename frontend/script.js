const API_BASE = "http://127.0.0.1:8000/route";
const SUBMIT_URL = `${API_BASE}/submission`;

const boilerplates = {
    cpp: `#include <iostream>\nusing namespace std;\n\nint main() {\n    int a, b;\n    if (cin >> a >> b) {\n        cout << "Sum is: " << (a + b) << endl;\n    }\n    return 0;\n}`,
    python: `import sys\n\ndef main():\n    input_data = sys.stdin.read().split()\n    if input_data:\n        a, b = int(input_data[0]), int(input_data[1])\n        print(f"Sum is: {a + b}")\n\nif __name__ == "__main__":\n    main()`
};

const defaultInputs = {
    cpp: "10 32\n",
    python: "10 32\n"
};

const languageSelect = document.getElementById("languageSelect");
const codeEditor = document.getElementById("codeEditor");
const inputData = document.getElementById("inputData");
const runBtn = document.getElementById("runBtn");
const outputConsole = document.getElementById("outputConsole");
const metaInfo = document.getElementById("metaInfo");

// Dashboard Elements
const statWaiting = document.getElementById("statWaiting");
const statActive = document.getElementById("statActive");
const statCompleted = document.getElementById("statCompleted");
const statFailed = document.getElementById("statFailed");
const refreshStatsBtn = document.getElementById("refreshStatsBtn");

const customJobIdInput = document.getElementById("customJobIdInput");
const fetchJobBtn = document.getElementById("fetchJobBtn");
const updateJobBtn = document.getElementById("updateJobBtn");
const deleteJobBtn = document.getElementById("deleteJobBtn");

const monitoredJobStatus = document.getElementById("monitoredJobStatus");
const monitoredJobCard = document.getElementById("monitoredJobCard");
const jobDetailsView = document.getElementById("jobDetailsView");

let activeJobPollInterval = null;

// Set initial content
codeEditor.value = boilerplates.cpp;
inputData.value = defaultInputs.cpp;

// Handle language change
languageSelect.addEventListener("change", (e) => {
    const lang = e.target.value;
    codeEditor.value = boilerplates[lang] || "";
    inputData.value = defaultInputs[lang] || "";
});

// Fetch overall Queue Statistics (QueueStats)
async function fetchQueueStats() {
    try {
        const res = await fetch(`${API_BASE}/queue-stats`);
        if (res.ok) {
            const data = await res.json();
            const stats = data.submissions || data;
            statWaiting.textContent = stats.in_queue ?? stats.waiting ?? 0;
            statActive.textContent = stats.processing ?? stats.active ?? 0;
            statCompleted.textContent = stats.completed ?? 0;
            statFailed.textContent = stats.failed ?? 0;
        }
    } catch (e) {
        console.warn("Queue stats route not reachable yet or offline.");
    }
}

// Fetch single job status from Redis cache
async function checkJobStatus(jobId, displayInConsole = true) {
    if (!jobId) return null;
    try {
        const res = await fetch(`${API_BASE}/submission/${jobId}`);
        if (!res.ok) {
            jobDetailsView.textContent = `Job ID ${jobId} not found in Redis cache.`;
            monitoredJobStatus.textContent = "Not Found";
            monitoredJobStatus.className = "badge badge-error";
            return null;
        }

        const data = await res.json();
        const status = data.status || data.payload?.status || "Unknown";
        
        // Update dashboard monitor card
        monitoredJobStatus.textContent = status;
        let badgeClass = "badge-pending";
        if (status === "Success" || status === "Completed") badgeClass = "badge-success";
        else if (status === "processing" || status === "Processing" || status === "Updated") badgeClass = "badge-processing";
        else if (status === "Failed" || status === "Error" || status.includes("Error") || status.includes("Exceeded")) badgeClass = "badge-error";
        monitoredJobStatus.className = `badge ${badgeClass}`;

        jobDetailsView.textContent = JSON.stringify(data, null, 2);

        if (displayInConsole) {
            renderResult(data);
        }

        return data;
    } catch (err) {
        jobDetailsView.textContent = `Error querying status: ${err.message}`;
        return null;
    }
}

// Start auto polling for submission progress
function startPollingJob(jobId) {
    if (activeJobPollInterval) clearInterval(activeJobPollInterval);

    // Immediately check status so UI monitor reflects queue state without waiting
    checkJobStatus(jobId, true);

    activeJobPollInterval = setInterval(async () => {
        const data = await checkJobStatus(jobId, true);
        fetchQueueStats();

        if (data) {
            const status = data.status || data.payload?.status;
            if (status === "Success" || status === "Completed" || status === "Failed" || status === "Error" || status === "Compilation Error" || status === "Runtime Error" || status === "Time Limit Exceeded") {
                clearInterval(activeJobPollInterval);
                activeJobPollInterval = null;
                runBtn.disabled = false;
                runBtn.innerHTML = `<span class="play-icon">▶</span> Run Code`;
            }
        }
    }, 500);
}

// Handle Run Code submit
runBtn.addEventListener("click", async () => {
    const language = languageSelect.value;
    const sourceCode = codeEditor.value;
    const input = inputData.value;

    if (!sourceCode.trim()) {
        alert("Please write some code first!");
        return;
    }

    const submissionId = "sub_" + Date.now();
    customJobIdInput.value = submissionId;

    // UI Loading state
    runBtn.disabled = true;
    runBtn.innerHTML = `<span class="play-icon">⏳</span> Pushing to Queue...`;
    outputConsole.className = "console";
    outputConsole.textContent = `Job ID: ${submissionId} submitted to BullMQ queue...\nWaiting for Worker to process...`;
    metaInfo.innerHTML = `<span class="badge badge-pending">Queued in Redis</span>`;

    // Reset job monitor card instantly
    monitoredJobStatus.textContent = "Pending";
    monitoredJobStatus.className = "badge badge-pending";
    jobDetailsView.textContent = JSON.stringify({ status: "Pending", submission_id: submissionId }, null, 2);

    try {
        const response = await fetch(SUBMIT_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id: submissionId,
                language: language,
                source_code: sourceCode,
                input_data: input
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const data = await response.json();
        
        // Start polling immediately
        startPollingJob(submissionId);
        fetchQueueStats();
    } catch (err) {
        outputConsole.className = "console error";
        outputConsole.textContent = `Execution Request Failed: ${err.message}\nEnsure backend server (python main.py) is running on http://127.0.0.1:8000!`;
        runBtn.disabled = false;
        runBtn.innerHTML = `<span class="play-icon">▶</span> Run Code`;
    }
});

// Manual Check Job
fetchJobBtn.addEventListener("click", () => {
    const jobId = customJobIdInput.value.trim();
    if (!jobId) return alert("Enter a Job ID first");
    checkJobStatus(jobId, true);
    fetchQueueStats();
});

// Manual Update Job Status in Cache
updateJobBtn.addEventListener("click", async () => {
    const jobId = customJobIdInput.value.trim();
    if (!jobId) return alert("Enter a Job ID first");

    const newStatus = prompt("Enter new status (e.g. Processing, Completed, Custom_Status):", "Updated");
    if (!newStatus) return;

    try {
        const res = await fetch(`${API_BASE}/submission/${jobId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) {
            alert(`Job ${jobId} updated in cache!`);
            checkJobStatus(jobId, true);
        } else {
            alert(`Update failed: ${res.statusText}`);
        }
    } catch (e) {
        alert(`Error updating job: ${e.message}`);
    }
});

// Manual Delete Job from Cache
deleteJobBtn.addEventListener("click", async () => {
    const jobId = customJobIdInput.value.trim();
    if (!jobId) return alert("Enter a Job ID first");

    if (!confirm(`Are you sure you want to delete job ${jobId} from Redis cache?`)) return;

    try {
        const res = await fetch(`${API_BASE}/submission/${jobId}`, {
            method: "DELETE"
        });
        if (res.ok) {
            alert(`Job ${jobId} deleted from cache!`);
            checkJobStatus(jobId, false);
            fetchQueueStats();
        } else {
            alert(`Delete failed: ${res.statusText}`);
        }
    } catch (e) {
        alert(`Error deleting job: ${e.message}`);
    }
});

// Refresh Stats Button
refreshStatsBtn.addEventListener("click", fetchQueueStats);

function renderResult(data) {
    const status = data.status || data.payload?.status || "Completed";
    const stdout = data.stdout || data.output || "";
    const stderr = data.stderr || data.error || "";
    const execution_time = data.execution_time ?? data.execution_time_ms ?? 0;
    const memory_usage = data.memory_usage || "0 MB";
    const exit_code = data.exit_code ?? null;

    let statusClass = "badge-error";
    if (status === "Success" || status === "Completed") statusClass = "badge-success";
    else if (status === "Pending") statusClass = "badge-pending";
    else if (status === "processing" || status === "Processing" || status === "Updated") statusClass = "badge-processing";

    metaInfo.innerHTML = `
        <span class="badge ${statusClass}">${status}</span>
        <span class="badge badge-time">⚡ ${execution_time}s</span>
        <span class="badge badge-time">💾 ${memory_usage}</span>
        ${exit_code !== null ? `<span class="badge badge-time">Exit: ${exit_code}</span>` : ''}
    `;

    if (status === "Pending" || status === "Processing") {
        outputConsole.className = "console";
        outputConsole.textContent = `Job ID: ${data.submission_id || customJobIdInput.value || ''} is currently ${status}...\nWaiting for Worker to complete execution...`;
        return;
    }

    if (status === "Success" || status === "Completed") {
        outputConsole.className = "console success";
        outputConsole.textContent = stdout || "(Execution completed with no output)";
    } else {
        outputConsole.className = "console error";
        let fullError = "";
        if (stderr) fullError += stderr + "\n";
        if (stdout) fullError += stdout;
        outputConsole.textContent = fullError.trim() || `Execution finished with status: ${status}`;
    }
}

// Initial stats fetch on load
fetchQueueStats();
setInterval(fetchQueueStats, 3000);


