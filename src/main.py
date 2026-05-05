"""
Main application entry point for the FastAPI server.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from src.api.main import app as api_app
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.database import async_engine, Base
from src.core.exceptions import TaskQueueException


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up distributed task queue application...")
    
    # Create database tables if they don't exist
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down distributed task queue application...")
    await async_engine.dispose()
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="Distributed Task Queue API",
    description="A scalable distributed task queue system with FastAPI, Celery, Redis, and PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.API_RELOAD else None,
    redoc_url="/redoc" if settings.API_RELOAD else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom exception handler
@app.exception_handler(TaskQueueException)
async def task_queue_exception_handler(request, exc: TaskQueueException):
    """Handle custom task queue exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": "Distributed Task Queue API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs" if settings.API_RELOAD else "disabled",
                "dashboard_url": "/dashboard",
    }


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
        """Presentation dashboard for the distributed task queue."""
        return """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Distributed Task Queue Dashboard</title>
    <style>
        :root {
            --bg: #07111f;
            --panel: rgba(12, 24, 43, 0.88);
            --text: #eef4ff;
            --muted: #9fb0cc;
            --accent: #67e8f9;
            --accent-2: #a78bfa;
            --success: #34d399;
            --warning: #fbbf24;
            --danger: #fb7185;
            --border: rgba(148, 163, 184, 0.18);
            --shadow: 0 30px 80px rgba(2, 6, 23, 0.45);
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text);
            font-family: "Aptos", "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(103, 232, 249, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(167, 139, 250, 0.20), transparent 24%),
                linear-gradient(180deg, #050b16 0%, #09172a 45%, #07111f 100%);
        }

        .wrap { max-width: 1280px; margin: 0 auto; padding: 28px 20px 56px; }
        .hero { display: grid; grid-template-columns: 1.7fr 1fr; gap: 20px; align-items: stretch; margin-bottom: 20px; }
        .panel, .card {
            background: var(--panel);
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            backdrop-filter: blur(16px);
            border-radius: 22px;
        }

        .hero-main {
            padding: 28px;
            position: relative;
            overflow: hidden;
            min-height: 360px;
        }
        .hero-main::before, .hero-main::after {
            content: "";
            position: absolute;
            border-radius: 50%;
            pointer-events: none;
        }
        .hero-main::before {
            inset: auto auto -40px -30px;
            width: 260px; height: 260px;
            background: radial-gradient(circle, rgba(103, 232, 249, 0.26), transparent 70%);
        }
        .hero-main::after {
            inset: -50px -30px auto auto;
            width: 220px; height: 220px;
            background: radial-gradient(circle, rgba(167, 139, 250, 0.22), transparent 68%);
        }

        .eyebrow {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 12px; border-radius: 999px;
            background: rgba(103, 232, 249, 0.10); color: var(--accent);
            font-size: 13px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
        }
        h1 { margin: 18px 0 10px; font-size: clamp(34px, 5vw, 58px); line-height: 0.96; letter-spacing: -0.05em; }
        .subtitle { max-width: 68ch; margin: 0; color: var(--muted); font-size: 16px; line-height: 1.75; }
        .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 22px; }
        .btn, .btn-secondary {
            border: 0; border-radius: 14px; padding: 12px 16px; text-decoration: none; font-weight: 700;
            cursor: pointer; transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
            display: inline-flex; align-items: center; gap: 10px;
        }
        .btn { color: #07111f; background: linear-gradient(135deg, var(--accent), #e0f2fe); box-shadow: 0 16px 30px rgba(103, 232, 249, 0.20); }
        .btn-secondary { color: var(--text); background: rgba(148, 163, 184, 0.12); border: 1px solid var(--border); }
        .btn:hover, .btn-secondary:hover { transform: translateY(-1px); }

        .hero-aside { display: grid; gap: 16px; }
        .stat-card {
            padding: 18px;
            background: linear-gradient(180deg, rgba(16, 35, 63, 0.95), rgba(10, 20, 38, 0.92));
            border: 1px solid var(--border); border-radius: 20px;
        }
        .stat-label { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }
        .stat-value { margin-top: 10px; font-size: 30px; font-weight: 800; letter-spacing: -0.03em; }
        .stat-note { margin-top: 6px; color: var(--muted); font-size: 14px; line-height: 1.55; }

        .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; margin-top: 20px; }
        .card { padding: 22px; }
        .span-4 { grid-column: span 4; } .span-6 { grid-column: span 6; } .span-8 { grid-column: span 8; } .span-12 { grid-column: span 12; }
        .section-title { margin: 0 0 8px; font-size: 18px; letter-spacing: -0.02em; }
        .section-subtitle { margin: 0 0 18px; color: var(--muted); line-height: 1.6; font-size: 14px; }

        .chip-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
        .chip {
            display: inline-flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 999px;
            background: rgba(148, 163, 184, 0.11); border: 1px solid var(--border); color: var(--text); font-size: 13px;
        }
        .chip strong { font-size: 14px; }

        .status-list { display: grid; gap: 12px; }
        .status-item {
            display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 14px 16px;
            border-radius: 16px; background: rgba(15, 24, 42, 0.92); border: 1px solid var(--border);
        }
        .status-name { font-weight: 700; }
        .status-meta { color: var(--muted); font-size: 13px; line-height: 1.4; }
        .badge {
            padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; letter-spacing: 0.03em; text-transform: uppercase;
        }
        .badge.success { background: rgba(52, 211, 153, 0.15); color: var(--success); }
        .badge.warning { background: rgba(251, 191, 36, 0.15); color: var(--warning); }
        .badge.danger { background: rgba(251, 113, 133, 0.15); color: var(--danger); }
        .badge.info { background: rgba(103, 232, 249, 0.15); color: var(--accent); }

        .form { display: grid; gap: 14px; }
        .form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
        label { display: block; margin: 0 0 8px; color: var(--muted); font-size: 13px; font-weight: 700; }
        input, select, textarea {
            width: 100%; border: 1px solid var(--border); border-radius: 14px; background: rgba(5, 11, 22, 0.65);
            color: var(--text); padding: 12px 14px; font: inherit; outline: none;
        }
        textarea { min-height: 180px; resize: vertical; font-family: "Cascadia Mono", Consolas, monospace; line-height: 1.6; }

        .chart-wrap { display: grid; gap: 14px; }
        .chart { display: grid; gap: 10px; }
        .bar-row { display: grid; grid-template-columns: 160px 1fr 60px; gap: 12px; align-items: center; }
        .bar-track {
            height: 12px; border-radius: 999px; overflow: hidden; background: rgba(148, 163, 184, 0.10); border: 1px solid var(--border);
        }
        .bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
        .bar-value { text-align: right; color: var(--muted); font-weight: 700; font-size: 13px; }

        .timeline {
            display: grid; gap: 12px;
        }
        .timeline-item {
            position: relative; padding: 14px 16px 14px 20px; border-radius: 16px; background: rgba(15, 24, 42, 0.92); border: 1px solid var(--border);
        }
        .timeline-item::before {
            content: ""; position: absolute; left: 10px; top: 18px; width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
            box-shadow: 0 0 0 4px rgba(103, 232, 249, 0.12);
        }
        .timeline-title { margin-left: 8px; font-weight: 700; }
        .timeline-meta { margin-left: 8px; color: var(--muted); font-size: 13px; margin-top: 4px; line-height: 1.45; }

        pre {
            margin: 0; white-space: pre-wrap; word-break: break-word; background: rgba(5, 11, 22, 0.75);
            border: 1px solid var(--border); border-radius: 16px; padding: 16px; overflow: auto; color: #dbeafe;
        }
        .result-box {
            transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
        }
        .result-box.is-pending {
            border-color: rgba(251, 191, 36, 0.35);
            box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.12);
        }
        .result-box.is-success {
            border-color: rgba(52, 211, 153, 0.40);
            box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.15);
            background: rgba(6, 17, 22, 0.86);
        }
        .result-box.is-danger {
            border-color: rgba(251, 113, 133, 0.45);
            box-shadow: inset 0 0 0 1px rgba(251, 113, 133, 0.15);
            background: rgba(24, 12, 18, 0.86);
        }
        .footer-note { margin-top: 18px; color: var(--muted); font-size: 13px; line-height: 1.6; }

        .task-table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; }
        .task-table th, .task-table td {
            padding: 12px 10px; text-align: left; border-bottom: 1px solid rgba(148, 163, 184, 0.12); font-size: 13px;
        }
        .task-table th { color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; font-size: 12px; }
        .task-table tr:hover td { background: rgba(103, 232, 249, 0.04); }

        @media (max-width: 1100px) {
            .hero, .grid, .form-row { grid-template-columns: 1fr; }
            .span-4, .span-6, .span-8, .span-12 { grid-column: span 1; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <section class="hero">
            <div class="panel hero-main">
                <div class="eyebrow">Distributed Task Queue Demo</div>
                <h1>Background jobs, visible in real time.</h1>
                <p class="subtitle">
                    This dashboard sits on top of FastAPI, Celery, Redis, and PostgreSQL. It is designed for demos: you can show the request,
                    the queued job, the worker execution, and the monitoring layer in one flow.
                </p>
                <div class="actions">
                    <a class="btn" href="/api/v1/docs" target="_blank" rel="noreferrer">Open API Docs</a>
                    <a class="btn-secondary" href="http://localhost:5555" target="_blank" rel="noreferrer">Open Flower</a>
                    <button class="btn-secondary" type="button" onclick="refreshAll()">Refresh dashboard</button>
                </div>
                <div class="chip-row">
                    <div class="chip"><strong>Use case:</strong> email, reports, imports</div>
                    <div class="chip"><strong>Demo:</strong> submit task → show Flower → show status</div>
                    <div class="chip"><strong>Backend:</strong> Redis + Celery workers</div>
                </div>
            </div>

            <div class="hero-aside">
                <div class="stat-card">
                    <div class="stat-label">Project purpose</div>
                    <div class="stat-value">Async work</div>
                    <div class="stat-note">Move slow work off the request thread so the app stays responsive.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Demo value</div>
                    <div class="stat-value">Queue + monitor</div>
                    <div class="stat-note">This is the quickest way to explain why a distributed task queue matters.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Top takeaway</div>
                    <div class="stat-value">Visible flow</div>
                    <div class="stat-note">Request goes in, worker handles it later, Flower shows it live.</div>
                </div>
            </div>
        </section>

        <section class="grid">
            <div class="card span-4">
                <h2 class="section-title">Live system snapshot</h2>
                <p class="section-subtitle">Health and monitoring status from the running app.</p>
                <div class="status-list" id="system-stats">
                    <div class="status-item"><div><div class="status-name">API health</div><div class="status-meta">Loading…</div></div><span class="badge warning">Pending</span></div>
                </div>
            </div>

            <div class="card span-8">
                <h2 class="section-title">Queues and workers</h2>
                <p class="section-subtitle">These are the pieces you narrate when showing the architecture.</p>
                <div class="grid" style="margin-top:0; gap:16px;">
                    <div class="card span-6" style="background: rgba(8, 15, 28, 0.65); box-shadow:none;">
                        <h3 class="section-title" style="font-size:16px;">Queues</h3>
                        <div class="status-list" id="queue-list">
                            <div class="status-item"><div><div class="status-name">Loading queue stats</div><div class="status-meta">Waiting for API response</div></div><span class="badge warning">…</span></div>
                        </div>
                    </div>
                    <div class="card span-6" style="background: rgba(8, 15, 28, 0.65); box-shadow:none;">
                        <h3 class="section-title" style="font-size:16px;">Workers</h3>
                        <div class="status-list" id="worker-list">
                            <div class="status-item"><div><div class="status-name">Loading worker info</div><div class="status-meta">Waiting for API response</div></div><span class="badge warning">…</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card span-6">
                <h2 class="section-title">Send a demo task</h2>
                <p class="section-subtitle">Submit a background job and then show it in Flower.</p>
                <form class="form" id="task-form">
                    <div class="form-row">
                        <div>
                            <label for="task_type">Task type</label>
                            <select id="task_type">
                                <option value="process_data">process_data</option>
                                <option value="send_notification">send_notification</option>
                                <option value="generate_report">generate_report</option>
                                <option value="cleanup_data">cleanup_data</option>
                                <option value="health_check">health_check</option>
                            </select>
                        </div>
                        <div>
                            <label for="processing_type">Processing type</label>
                            <input id="processing_type" value="demo" />
                        </div>
                    </div>
                    <div>
                        <label for="task_data">Task JSON</label>
                        <textarea id="task_data">{
    "customer_id": 101,
    "records": [1, 2, 3, 4]
}</textarea>
                    </div>
                    <div class="actions" style="margin-top:0;">
                        <button class="btn" type="submit">Submit task</button>
                        <button class="btn-secondary" type="button" onclick="fillSample()">Load sample</button>
                    </div>
                </form>
            </div>

            <div class="card span-6">
                <h2 class="section-title">Response / status</h2>
                <p class="section-subtitle">Narrate the submission result and then switch to Flower.</p>
                <pre id="output">Waiting for a task submission…</pre>
                <div class="footer-note">Demo flow: open the dashboard, submit a task, switch to Flower, then show the status endpoint.</div>
            </div>

            <div class="card span-6">
                <h2 class="section-title">Task history</h2>
                <p class="section-subtitle">A quick history table to show recent tasks and their states.</p>
                <table class="task-table" aria-label="Task history">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Function</th>
                            <th>Status</th>
                            <th>Priority</th>
                        </tr>
                    </thead>
                    <tbody id="task-history">
                        <tr><td colspan="4" style="color: var(--muted);">Loading task history…</td></tr>
                    </tbody>
                </table>
            </div>

            <div class="card span-6">
                <h2 class="section-title">Latest task status</h2>
                <p class="section-subtitle">This follows the most recent submitted task so you can show its live lifecycle.</p>
                <div class="status-list" id="latest-task-status">
                    <div class="status-item"><div><div class="status-name">Waiting for task data</div><div class="status-meta">Submit a task or let the dashboard load the newest stored one.</div></div><span class="badge info">Ready</span></div>
                </div>
                <div style="margin-top: 14px;">
                    <label for="latest-task-result">Latest task result</label>
                    <pre id="latest-task-result" class="result-box is-pending">Result will appear here when the task completes.</pre>
                </div>
            </div>

            <div class="card span-6">
                <h2 class="section-title">Task throughput chart</h2>
                <p class="section-subtitle">A simple chart using the monitoring metrics endpoint.</p>
                <div class="chart-wrap" id="metrics-chart">
                    <div class="status-item"><div><div class="status-name">Loading metrics</div><div class="status-meta">Waiting for API response</div></div><span class="badge warning">…</span></div>
                </div>
            </div>

            <div class="card span-6">
                <h2 class="section-title">How to explain the demo</h2>
                <div class="timeline">
                    <div class="timeline-item">
                        <div class="timeline-title">1. Submit a task</div>
                        <div class="timeline-meta">Use the form here or the API docs to send a background job request.</div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-title">2. Show the worker</div>
                        <div class="timeline-meta">Open Flower to show the job queue and worker activity in real time.</div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-title">3. Show status and monitoring</div>
                        <div class="timeline-meta">Use the task status endpoint and queue metrics to prove observability.</div>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <script>
        const apiBase = "/api/v1";
        let lastSubmittedTaskId = null;

        function badgeForStatus(status) {
            const normalized = String(status || "unknown").toLowerCase();
            if (["healthy", "running", "active", "success", "up"].includes(normalized)) return ["success", String(status).toUpperCase()];
            if (["starting", "pending", "idle", "progress"].includes(normalized)) return ["warning", String(status).toUpperCase()];
            return ["danger", String(status).toUpperCase()];
        }

        function escapeHtml(value) {
            return String(value)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;");
        }

        function renderList(elementId, items, emptyMarkup) {
            const el = document.getElementById(elementId);
            el.innerHTML = items.length ? items.join("") : emptyMarkup;
        }

        function setResultBoxState(state) {
            const resultBox = document.getElementById("latest-task-result");
            resultBox.classList.remove("is-pending", "is-success", "is-danger");
            resultBox.classList.add(state);
        }

        function renderMetrics(metrics) {
            const container = document.getElementById("metrics-chart");
            if (!metrics || !metrics.length) {
                container.innerHTML = '<div class="status-item"><div><div class="status-name">No metric data</div><div class="status-meta">The API returned an empty response.</div></div><span class="badge warning">Empty</span></div>';
                return;
            }

            const maxCount = Math.max(...metrics.map(item => item.total_count), 1);
            const bars = metrics.map(item => {
                const width = Math.max(8, Math.round((item.total_count / maxCount) * 100));
                return `
                    <div class="bar-row">
                        <div>
                            <div class="status-name">${escapeHtml(item.task_name)}</div>
                            <div class="status-meta">${item.success_count} success / ${item.failure_count} failed</div>
                        </div>
                        <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
                        <div class="bar-value">${item.total_count}</div>
                    </div>`;
            });

            container.innerHTML = bars.join("");
        }

        function renderTaskHistory(tasks) {
            const tbody = document.getElementById("task-history");
            if (!tasks || !tasks.length) {
                tbody.innerHTML = '<tr><td colspan="4" style="color: var(--muted);">No tasks found.</td></tr>';
                return;
            }

            tbody.innerHTML = tasks.map(task => {
                const [tone, label] = badgeForStatus(task.status);
                return `
                    <tr>
                        <td>${escapeHtml(task.name)}</td>
                        <td>${escapeHtml(task.function_name)}</td>
                        <td><span class="badge ${tone}">${escapeHtml(label)}</span></td>
                        <td>${escapeHtml(task.priority)}</td>
                    </tr>`;
            }).join("");
        }

        async function renderLatestTaskStatus(taskId) {
            const container = document.getElementById("latest-task-status");
            const resultBox = document.getElementById("latest-task-result");
            if (!taskId) {
                container.innerHTML = '<div class="status-item"><div><div class="status-name">No task selected</div><div class="status-meta">Submit a task to see its live status here.</div></div><span class="badge warning">Idle</span></div>';
                resultBox.textContent = "Result will appear here when the task completes.";
                setResultBoxState("is-pending");
                return;
            }

            container.innerHTML = '<div class="status-item"><div><div class="status-name">Loading latest task</div><div class="status-meta">Fetching status for the newest task.</div></div><span class="badge warning">Loading</span></div>';
            resultBox.textContent = "Checking for a completed result...";
            setResultBoxState("is-pending");

            try {
                const response = await fetch(`${apiBase}/tasks/status/${taskId}`);
                const status = await response.json();
                const [tone, label] = badgeForStatus(status.database_status || status.status);
                const statusValue = String(status.database_status || status.status || "unknown").toUpperCase();
                const meta = [
                    `Task ID: ${status.task_id}`,
                    `API status: ${status.status}`,
                    status.database_status ? `Database status: ${status.database_status}` : null,
                    status.result ? `Result available` : null,
                    status.error ? `Error: ${status.error}` : null
                ].filter(Boolean).join(" | ");

                container.innerHTML = `
                    <div class="status-item">
                        <div>
                            <div class="status-name">${escapeHtml(status.task_id)}</div>
                            <div class="status-meta">${escapeHtml(meta)}</div>
                        </div>
                        <span class="badge ${tone}">${escapeHtml(label)}</span>
                    </div>`;

                if (["SUCCESS", "COMPLETED", "DONE"].includes(statusValue)) {
                    try {
                        const resultResponse = await fetch(`${apiBase}/tasks/${taskId}/result`);
                        const resultData = await resultResponse.json();
                        resultBox.textContent = JSON.stringify(resultData, null, 2);
                        setResultBoxState("is-success");
                    } catch (resultError) {
                        resultBox.textContent = `Could not load task result: ${resultError.message}`;
                        setResultBoxState("is-danger");
                    }
                } else if (["FAILURE", "FAILED", "REVOKED", "CANCELLED"].includes(statusValue)) {
                    resultBox.textContent = status.error ? `Task failed: ${status.error}` : `Task finished with status ${statusValue}.`;
                    setResultBoxState("is-danger");
                } else {
                    resultBox.textContent = `Task is currently ${statusValue}. Result will appear when it completes.`;
                    setResultBoxState("is-pending");
                }
            } catch (error) {
                container.innerHTML = '<div class="status-item"><div><div class="status-name">Unable to load latest task</div><div class="status-meta">The status endpoint returned an error.</div></div><span class="badge danger">Error</span></div>';
                resultBox.textContent = `Unable to load latest task result: ${error.message}`;
                setResultBoxState("is-danger");
            }
        }

        async function refreshAll() {
            const [healthRes, statsRes, queuesRes, workersRes, metricsRes, tasksRes] = await Promise.allSettled([
                fetch("/health").then(r => r.json()),
                fetch(`${apiBase}/monitoring/stats`).then(r => r.json()),
                fetch(`${apiBase}/monitoring/queues`).then(r => r.json()),
                fetch(`${apiBase}/monitoring/workers`).then(r => r.json()),
                fetch(`${apiBase}/monitoring/metrics?hours=24`).then(r => r.json()),
                fetch(`${apiBase}/tasks/?limit=8`).then(r => r.json())
            ]);

            const system = [];
            if (healthRes.status === "fulfilled") {
                const [tone, label] = badgeForStatus(healthRes.value.status);
                system.push(`<div class="status-item"><div><div class="status-name">API health</div><div class="status-meta">${escapeHtml(healthRes.value.timestamp)}</div></div><span class="badge ${tone}">${escapeHtml(label)}</span></div>`);
            } else {
                system.push('<div class="status-item"><div><div class="status-name">API health</div><div class="status-meta">Unable to load health endpoint</div></div><span class="badge danger">Error</span></div>');
            }

            if (statsRes.status === "fulfilled") {
                const s = statsRes.value;
                system.push(`<div class="status-item"><div><div class="status-name">Tasks</div><div class="status-meta">Total ${s.total_tasks} | Completed ${s.completed_tasks}</div></div><span class="badge success">Live</span></div>`);
                system.push(`<div class="status-item"><div><div class="status-name">Failures</div><div class="status-meta">Failed tasks ${s.failed_tasks}</div></div><span class="badge ${s.failed_tasks > 0 ? "warning" : "success"}">${s.failed_tasks > 0 ? "Watch" : "OK"}</span></div>`);
                system.push(`<div class="status-item"><div><div class="status-name">Workers</div><div class="status-meta">${Object.keys(s.workers || {}).length} workers reporting</div></div><span class="badge info">${Object.keys(s.workers || {}).length}</span></div>`);
            }
            renderList("system-stats", system, '<div class="status-item"><div><div class="status-name">No system data</div><div class="status-meta">The API returned an empty response.</div></div><span class="badge warning">Empty</span></div>');

            if (queuesRes.status === "fulfilled") {
                renderList("queue-list", queuesRes.value.map(q => `
                    <div class="status-item">
                        <div>
                            <div class="status-name">${escapeHtml(q.queue_name)}</div>
                            <div class="status-meta">Pending ${q.pending_tasks} | Active ${q.active_tasks} | Scheduled ${q.scheduled_tasks} | Failed ${q.failed_tasks}</div>
                        </div>
                        <span class="badge ${q.failed_tasks > 0 ? "warning" : "success"}">${q.pending_tasks + q.active_tasks}</span>
                    </div>`), '<div class="status-item"><div><div class="status-name">No queue data</div><div class="status-meta">The API returned an empty response.</div></div><span class="badge warning">Empty</span></div>');
            }

            if (workersRes.status === "fulfilled") {
                renderList("worker-list", workersRes.value.map(w => `
                    <div class="status-item">
                        <div>
                            <div class="status-name">${escapeHtml(w.worker_id)}</div>
                            <div class="status-meta">${escapeHtml(w.current_task || "Idle")} | Processed ${w.processed_tasks} | Failed ${w.failed_tasks}</div>
                        </div>
                        <span class="badge ${w.status === "active" ? "success" : "warning"}">${escapeHtml(w.status)}</span>
                    </div>`), '<div class="status-item"><div><div class="status-name">No worker data</div><div class="status-meta">The API returned an empty response.</div></div><span class="badge warning">Empty</span></div>');
            }

            if (metricsRes.status === "fulfilled") {
                renderMetrics(metricsRes.value);
            }

            if (tasksRes.status === "fulfilled") {
                renderTaskHistory(tasksRes.value);
                await renderLatestTaskStatus(lastSubmittedTaskId || (tasksRes.value[0] && tasksRes.value[0].id));
            }
        }

        function fillSample() {
            document.getElementById("task_type").value = "process_data";
            document.getElementById("processing_type").value = "demo";
            document.getElementById("task_data").value = JSON.stringify({ customer_id: 101, records: [1, 2, 3, 4] }, null, 2);
        }

        document.getElementById("task-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const task_type = document.getElementById("task_type").value;
            const processing_type = document.getElementById("processing_type").value || "demo";
            let data;

            try {
                data = JSON.parse(document.getElementById("task_data").value);
            } catch (error) {
                document.getElementById("output").textContent = `Invalid JSON: ${error.message}`;
                return;
            }

            const payload = { task_type, data, options: { processing_type } };
            document.getElementById("output").textContent = "Submitting task...";

            try {
                const response = await fetch(`${apiBase}/tasks/submit`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                lastSubmittedTaskId = result.task_id || null;
                document.getElementById("output").textContent = JSON.stringify(result, null, 2) + (lastSubmittedTaskId ? `\n\nNext: GET ${apiBase}/tasks/status/${lastSubmittedTaskId}` : "");
                await refreshAll();
            } catch (error) {
                document.getElementById("output").textContent = `Submission failed: ${error.message}`;
            }
        });

        refreshAll();
        setInterval(refreshAll, 8000);
    </script>
</body>
</html>"""

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

# Mount the main API
app.mount("/api/v1", api_app)

# Additional middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} - {process_time:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    import time
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=1 if settings.API_RELOAD else settings.API_WORKERS,
        log_config="logging.ini" if os.path.exists("logging.ini") else None,
    )