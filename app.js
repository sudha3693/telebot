const app = document.getElementById('app');
const API_BASE_URL = (window.API_BASE_URL || window.location.origin || 'http://10.138.25.47:8001').replace(/\/$/, '');

function resolveApiUrl(path) {
    if (/^https?:\/\//i.test(path)) {
        return path;
    }
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE_URL}${normalizedPath}`;
}

async function fetchWithRetry(path, options = {}, retries = 1) {
    const targetUrl = resolveApiUrl(path);
    let lastError = null;

    for (let attempt = 0; attempt <= retries; attempt += 1) {
        try {
            return await fetch(targetUrl, options);
        } catch (error) {
            lastError = error;
            console.error(`Network request failed (${attempt + 1}/${retries + 1})`, { targetUrl, error });
            if (attempt < retries) {
                await new Promise((resolve) => window.setTimeout(resolve, 500));
            }
        }
    }

    throw lastError || new Error(`Unable to reach ${targetUrl}`);
}

function normalizeSiteId(value) {
    return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
}

const state = {
    token: localStorage.getItem('admin_token') || '',
    tab: 'overview',
    stats: null,
    requests: [],
    users: [],
    logs: [],
    roleUsers: {
        active: [],
        pending: [],
        blocked: [],
        rejected: [],
        admins: [],
    },
    search: '',
};

function toast(message) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
}

async function api(url, options = {}) {
    const headers = options.headers || {};
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }
    const response = await fetchWithRetry(url, { ...options, headers });
    if (response.status === 401) {
        localStorage.removeItem('admin_token');
        state.token = '';
        render();
        throw new Error('Unauthorized');
    }
    return response;
}

function renderLogin() {
    app.innerHTML = `
        <div style="max-width:420px;margin:9vh auto" class="card">
            <h2 class="section-title">Admin Sign In</h2>
            <p class="tag">Telegram Bot Management Console V2</p>
            <form id="loginForm">
                <label>Username</label>
                <input name="username" required />
                <label style="margin-top:10px;display:block">Password</label>
                <input name="password" type="password" required />
                <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px">
                    <button class="btn primary" type="submit">Login</button>
                    <button class="btn" type="button" id="forgotBtn">Forgot password?</button>
                </div>
            </form>
        </div>
    `;

    document.getElementById('forgotBtn').onclick = () => {
        toast('Reset flow UI only. Add mail/SMS integration in production.');
    };

    document.getElementById('loginForm').onsubmit = async (event) => {
        event.preventDefault();
        const form = event.target;
        const body = new FormData();
        body.append('username', form.username.value.trim());
        body.append('password', form.password.value);
        try {
            const res = await fetchWithRetry('/api/login', { method: 'POST', body });
            if (!res.ok) {
                toast('Invalid credentials');
                return;
            }
            const data = await res.json();
            localStorage.setItem('admin_token', data.access_token);
            state.token = data.access_token;
            await bootstrap();
        } catch (err) {
            toast(`Login failed: ${err.message}`);
        }
    };
}

function navButton(id, label) {
    return `<button class="nav-btn ${state.tab === id ? 'active' : ''}" data-tab="${id}">${label}</button>`;
}

function renderDashboard() {
    const totals = state.stats?.totals || {};
    app.innerHTML = `
        <div class="layout">
            <aside class="sidebar">
                <div class="brand">TeleBot Control</div>
                <div class="tag">Enterprise Workflow Dashboard</div>
                ${navButton('overview', 'Overview')}
                ${navButton('access', 'Access Requests')}
                ${navButton('users', 'Users & Roles')}
                ${navButton('upload', 'Excel Upload Center')}
                ${navButton('search', 'Search & Filters')}
                ${navButton('logs', 'Activity Logs')}
                <hr style="border:none;border-top:1px solid var(--line);margin:18px 0" />
                <button class="btn" id="themeBtn">Toggle Light/Dark</button>
                <button class="btn danger" id="logoutBtn" style="margin-top:10px">Logout</button>
            </aside>
            <main class="main">
                <div class="topbar">
                    <h2 style="margin:0">Telegram Bot Management V2</h2>
                    <div style="display:flex;gap:8px">
                        <button class="btn" id="refreshBtn">Refresh</button>
                    </div>
                </div>

                <div id="overview" class="tab ${state.tab === 'overview' ? '' : 'hidden'}">
                    <div class="grid-cards">
                        <div class="card"><div class="metric-title">Total Users</div><div class="metric-value">${totals.users || 0}</div></div>
                        <div class="card"><div class="metric-title">Pending</div><div class="metric-value">${totals.pending || 0}</div></div>
                        <div class="card"><div class="metric-title">Active</div><div class="metric-value">${totals.active || 0}</div></div>
                        <div class="card"><div class="metric-title">Rejected</div><div class="metric-value">${totals.rejected || 0}</div></div>
                        <div class="card"><div class="metric-title">Blocked</div><div class="metric-value">${totals.blocked || 0}</div></div>
                        <div class="card"><div class="metric-title">Admins</div><div class="metric-value">${totals.admins || 0}</div></div>
                        <div class="card"><div class="metric-title">Sites</div><div class="metric-value">${totals.sites || 0}</div></div>
                        <div class="card"><div class="metric-title">Pending Requests</div><div class="metric-value">${totals.pending_requests || 0}</div></div>
                        <div class="card"><div class="metric-title">Searches</div><div class="metric-value">${totals.searches || 0}</div></div>
                    </div>
                    <div class="row">
                        <div class="card">
                            <h3 class="section-title">Recent Access Requests</h3>
                            ${renderRequestsTable((state.stats?.recent_access_requests || []).slice(0, 6), false)}
                        </div>
                        <div class="card">
                            <h3 class="section-title">Status Split</h3>
                            <canvas id="statusChart" height="240"></canvas>
                        </div>
                    </div>
                    <div class="row">
                        <div class="card">
                            <h3 class="section-title">Top Searched Sites</h3>
                            ${renderTopSites(state.stats?.top_sites || [])}
                        </div>
                        <div class="card">
                            <h3 class="section-title">Telecom KPI Summary</h3>
                            <canvas id="kpiChart" height="240"></canvas>
                        </div>
                    </div>
                    <div class="row">
                        <div class="card">
                            <h3 class="section-title">Climate Analytics</h3>
                            <canvas id="climateChart" height="240"></canvas>
                        </div>
                        <div class="card">
                            <h3 class="section-title">Technology Distribution</h3>
                            <canvas id="techChart" height="240"></canvas>
                        </div>
                    </div>
                </div>

                <div id="access" class="tab ${state.tab === 'access' ? '' : 'hidden'}">
                    <div class="card">
                        <h3 class="section-title">Access Approval Queue</h3>
                        ${renderRequestsTable(state.requests, true)}
                    </div>
                </div>

                <div id="users" class="tab ${state.tab === 'users' ? '' : 'hidden'}">
                    <div class="card">
                        <h3 class="section-title">Authorized Users</h3>
                        ${renderUserTable(state.roleUsers.active || [], ['unapprove', 'block', 'make_admin'])}
                    </div>
                    <div class="card" style="margin-top:14px">
                        <h3 class="section-title">Pending Requests</h3>
                        ${renderUserTable(state.roleUsers.pending || [], ['approve', 'reject', 'block'])}
                    </div>
                    <div class="card" style="margin-top:14px">
                        <h3 class="section-title">Blocked Users</h3>
                        ${renderUserTable(state.roleUsers.blocked || [], ['unblock'])}
                    </div>
                    <div class="card" style="margin-top:14px">
                        <h3 class="section-title">Rejected Users</h3>
                        ${renderUserTable(state.roleUsers.rejected || [], ['unreject'])}
                    </div>
                    <div class="card" style="margin-top:14px">
                        <h3 class="section-title">Admin Users</h3>
                        ${renderUserTable(state.roleUsers.admins || [], ['remove_admin'])}
                    </div>
                </div>

                <div id="upload" class="tab ${state.tab === 'upload' ? '' : 'hidden'}">
                    <div class="card">
                        <h3 class="section-title">Intelligent Excel Upload</h3>
                        <div class="row" style="grid-template-columns:1fr 1fr;">
                            <div>
                                <label>Dataset</label>
                                <select id="datasetSel">
                                    <option value="daywise">4G Day Wise</option>
                                    <option value="nwa">4G NWA Trend</option>
                                </select>
                                <label style="margin-top:10px;display:block">Excel File</label>
                                <input id="uploadFile" type="file" accept=".xlsx,.xls" />
                                <div style="display:flex;gap:8px;margin-top:12px;">
                                    <button class="btn" id="previewBtn">Preview & Validate</button>
                                    <button class="btn primary" id="importBtn">Import Data</button>
                                </div>
                            </div>
                            <div>
                                <h4 style="margin:0 0 8px">Validation Output</h4>
                                <pre id="previewOut" style="white-space:pre-wrap;background:var(--panel-solid);border:1px solid var(--line);padding:10px;border-radius:12px;min-height:150px"></pre>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="search" class="tab ${state.tab === 'search' ? '' : 'hidden'}">
                    <div class="card" style="margin-bottom:16px;">
                        <h3 class="section-title">Search Sites</h3>
                        <p class="muted" style="margin-top:0;">Use exact or partial site IDs. Case, spaces, and hyphens are ignored. Example: <code>bhpat01</code>, <code>Bhpat-01</code>, <code>2ry6y</code>.</p>
                        <div style="display:grid;grid-template-columns:2fr auto;gap:8px;margin-bottom:10px;">
                            <input id="siteLookupInput" placeholder="Search site by ID, partial ID, or formatted code" />
                            <button class="btn" id="siteLookupBtn">Find Site</button>
                        </div>
                        <div id="siteLookupStatus" class="muted"></div>
                        <div class="table-wrap"><table><thead><tr><th>Sr ID</th><th>Primary Site ID</th><th>Alt Site ID</th><th>Site Name</th><th>District</th></tr></thead><tbody id="siteLookupBody"><tr><td colspan="5">Enter a site query to search.</td></tr></tbody></table></div>
                    </div>
                    <div class="card">
                        <h3 class="section-title">Search Users</h3>
                        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
                            <input id="searchInput" placeholder="Search by name, username, telegram id" value="${state.search}" />
                            <select id="statusFilter">
                                <option value="">All Status</option>
                                <option value="pending">Pending</option>
                                <option value="active">Active</option>
                                <option value="rejected">Rejected</option>
                                <option value="blocked">Blocked</option>
                            </select>
                            <select id="sortBy"><option value="id">Sort: ID</option><option value="username">Username</option><option value="telegram_id">Telegram ID</option><option value="status">Status</option></select>
                            <button class="btn" id="searchBtn">Search</button>
                        </div>
                        <div class="table-wrap"><table><thead><tr><th>ID</th><th>Telegram ID</th><th>Username</th><th>Name</th><th>Status</th></tr></thead><tbody id="searchBody"></tbody></table></div>
                    </div>
                </div>

                <div id="logs" class="tab ${state.tab === 'logs' ? '' : 'hidden'}">
                    <div class="card">
                        <h3 class="section-title">Audit Logs</h3>
                        <div class="table-wrap"><table><thead><tr><th>Action</th><th>Target</th><th>Details</th><th>Time</th></tr></thead><tbody id="activityBody"></tbody></table></div>
                    </div>
                </div>
            </main>
        </div>
    `;

    bindDashboardEvents();
    if (state.tab === 'overview') {
        renderChart(totals);
        renderSimpleChart('kpiChart', state.stats?.kpi_summary || [], ['#1166ff', '#00a59b', '#f2b441', '#c53d43']);
        renderSimpleChart('climateChart', state.stats?.climate_distribution || [], ['#00a59b', '#1166ff', '#f2b441', '#6f5ce8']);
        renderSimpleChart('techChart', state.stats?.tech_distribution || [], ['#1166ff', '#00a59b', '#f2b441', '#c53d43']);
    }
}

function renderRequestsTable(rows, withActions) {
    const body = rows.map((row) => `
        <tr>
            <td>${row.id}</td>
            <td>${row.telegram_id || '-'}</td>
            <td>${row.username || '-'}</td>
            <td>${row.full_name || '-'}</td>
            <td>${row.status || '-'}</td>
            <td>${row.requested_at ? new Date(row.requested_at).toLocaleString() : '-'}</td>
            <td>
                ${withActions ? `<div class="row-actions">
                    <button class="btn" data-action="approve" data-id="${row.id}">Approve</button>
                    <button class="btn" data-action="reject" data-id="${row.id}">Reject</button>
                    <button class="btn danger" data-action="block" data-id="${row.id}">Block</button>
                </div>` : '-'}
            </td>
        </tr>
    `).join('');

    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>ID</th><th>Telegram ID</th><th>Username</th><th>Name</th><th>Status</th><th>Requested</th><th>Actions</th></tr></thead>
                <tbody>${body || '<tr><td colspan="7">No records.</td></tr>'}</tbody>
            </table>
        </div>
    `;
}

function renderTopSites(rows) {
    if (!rows.length) {
        return '<div class="muted">No search analytics yet.</div>';
    }
    const body = rows.map((row) => `
        <tr>
            <td>${row.site_id || '-'}</td>
            <td>${row.total || 0}</td>
        </tr>
    `).join('');

    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>Site ID</th><th>Searches</th></tr></thead>
                <tbody>${body}</tbody>
            </table>
        </div>
    `;
}

function renderUserTable(rows, actions) {
    const body = rows.map((row) => `
        <tr>
            <td>${row.id}</td>
            <td>${row.telegram_id || '-'}</td>
            <td>${row.username || '-'}</td>
            <td>${row.full_name || '-'}</td>
            <td>${row.role || '-'}</td>
            <td>${row.status || '-'}</td>
            <td>
                <div class="row-actions">
                    ${actions.map((action) => `
                        <button class="btn ${action === 'block' ? 'danger' : ''}" data-user-action="${action}" data-user-id="${row.id}">
                            ${action.replace('_', ' ').toUpperCase()}
                        </button>
                    `).join('')}
                </div>
            </td>
        </tr>
    `).join('');

    return `
        <div class="table-wrap">
            <table>
                <thead><tr><th>ID</th><th>Telegram ID</th><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>${body || '<tr><td colspan="7">No records.</td></tr>'}</tbody>
            </table>
        </div>
    `;
}

function renderChart(totals) {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;
    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Active', 'Rejected', 'Blocked'],
            datasets: [{
                data: [totals.pending || 0, totals.active || 0, totals.rejected || 0, totals.blocked || 0],
                backgroundColor: ['#f2b441', '#0f9f63', '#c53d43', '#6f5ce8']
            }]
        },
        options: { plugins: { legend: { labels: { color: getComputedStyle(document.body).getPropertyValue('--text') } } } }
    });
}

function renderSimpleChart(canvasId, rows, colors) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const labels = rows.map((row) => row.label || 'Unknown');
    const values = rows.map((row) => row.total || 0);
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, Math.max(values.length, 1)),
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: getComputedStyle(document.body).getPropertyValue('--text') } },
                y: { ticks: { color: getComputedStyle(document.body).getPropertyValue('--text') } },
            },
        }
    });
}

function bindDashboardEvents() {
    document.querySelectorAll('.nav-btn').forEach((btn) => {
        btn.onclick = () => {
            state.tab = btn.dataset.tab;
            renderDashboard();
            if (state.tab === 'logs') loadActivityLogs();
            if (state.tab === 'users') loadUserManagement();
        };
    });

    document.getElementById('logoutBtn').onclick = () => {
        localStorage.removeItem('admin_token');
        state.token = '';
        render();
    };

    document.getElementById('themeBtn').onclick = () => {
        const current = document.body.getAttribute('data-theme');
        document.body.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
    };

    document.getElementById('refreshBtn').onclick = bootstrap;

    document.querySelectorAll('[data-action]').forEach((btn) => {
        btn.onclick = async () => {
            const id = btn.dataset.id;
            const action = btn.dataset.action;
            const res = await api(`/api/v2/access-requests/${id}?decision=${action}`, { method: 'PATCH' });
            if (!res.ok) {
                toast(`Failed to ${action} request`);
                return;
            }
            toast(`Request ${id} updated: ${action}`);
            await bootstrap();
        };
    });

    document.querySelectorAll('[data-user-action]').forEach((btn) => {
        btn.onclick = async () => {
            const id = btn.dataset.userId;
            const action = btn.dataset.userAction;
            const routeMap = {
                approve: 'approve',
                unapprove: 'unapprove',
                reject: 'reject',
                unreject: 'unreject',
                block: 'block',
                unblock: 'unblock',
                make_admin: 'make-admin',
                remove_admin: 'remove-admin',
            };
            const route = routeMap[action];
            if (!route) return;
            const res = await api(`/api/users/${id}/${route}`, { method: 'PATCH' });
            if (!res.ok) {
                toast(`Failed to ${action} user`);
                return;
            }
            toast(`User ${id} updated: ${action}`);
            await bootstrap();
        };
    });

    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
        searchBtn.onclick = loadSearch;
    }

    const siteLookupBtn = document.getElementById('siteLookupBtn');
    if (siteLookupBtn) {
        siteLookupBtn.onclick = loadSiteLookup;
    }

    const siteLookupInput = document.getElementById('siteLookupInput');
    if (siteLookupInput) {
        siteLookupInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                loadSiteLookup();
            }
        });
    }

    const previewBtn = document.getElementById('previewBtn');
    if (previewBtn) {
        previewBtn.onclick = previewUpload;
    }

    const importBtn = document.getElementById('importBtn');
    if (importBtn) {
        importBtn.onclick = importUpload;
    }

    loadSearch();
}

async function loadSiteLookup() {
    const input = document.getElementById('siteLookupInput');
    const status = document.getElementById('siteLookupStatus');
    const tbody = document.getElementById('siteLookupBody');
    if (!input || !status || !tbody) return;

    const rawQuery = input.value || '';
    const normalizedQuery = normalizeSiteId(rawQuery);
    if (!normalizedQuery) {
        status.textContent = 'Enter at least one letter or number from the site ID.';
        tbody.innerHTML = '<tr><td colspan="5">No site query entered.</td></tr>';
        return;
    }

    status.textContent = `Searching normalized site ID: ${normalizedQuery}`;

    try {
        const res = await api(`/api/sites/search-options?site_id=${encodeURIComponent(rawQuery)}&limit=10`);
        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(errorText || 'Site lookup failed');
        }

        const rows = await res.json();
        if (!rows.length) {
            status.textContent = `No sites matched ${rawQuery}. Try a shorter partial query.`;
            tbody.innerHTML = '<tr><td colspan="5">No matching sites.</td></tr>';
            return;
        }

        status.textContent = `Found ${rows.length} matching site${rows.length === 1 ? '' : 's'}. Best match shown first.`;
        tbody.innerHTML = rows.map((row) => `
            <tr>
                <td>${row.sr_id || '-'}</td>
                <td>${row.site_id || '-'}</td>
                <td>${row.site_id_2 || row.site_id_3 || '-'}</td>
                <td>${row.airtel_site_name || '-'}</td>
                <td>${row.district || row.dist || '-'}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Site lookup failed', error);
        status.textContent = 'Site lookup failed. Check the API connection and try again.';
        tbody.innerHTML = '<tr><td colspan="5">Site lookup failed.</td></tr>';
    }
}

async function loadSearch() {
    const input = document.getElementById('searchInput');
    const status = document.getElementById('statusFilter');
    const sortBy = document.getElementById('sortBy');
    if (!input || !status || !sortBy) return;

    const q = encodeURIComponent(input.value || '');
    const st = encodeURIComponent(status.value || '');
    const sb = encodeURIComponent(sortBy.value || 'id');

    const res = await api(`/api/v2/search?q=${q}&status=${st}&sort_by=${sb}&order=desc`);
    const rows = await res.json();
    const tbody = document.getElementById('searchBody');
    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${row.id}</td>
            <td>${row.telegram_id || '-'}</td>
            <td>${row.username || '-'}</td>
            <td>${row.full_name || '-'}</td>
            <td>${row.status || '-'}</td>
        </tr>
    `).join('') || '<tr><td colspan="5">No matching users</td></tr>';
}

async function previewUpload() {
    const dataset = document.getElementById('datasetSel').value;
    const file = document.getElementById('uploadFile').files[0];
    const output = document.getElementById('previewOut');
    if (!file) {
        toast('Choose a file first');
        return;
    }
    const body = new FormData();
    body.append('file', file);

    const res = await api(`/api/v2/uploads/preview?dataset=${dataset}`, { method: 'POST', body });
    const data = await res.json();
    output.textContent = JSON.stringify(data, null, 2);
}

async function importUpload() {
    const dataset = document.getElementById('datasetSel').value;
    const file = document.getElementById('uploadFile').files[0];
    const output = document.getElementById('previewOut');
    if (!file) {
        toast('Choose a file first');
        return;
    }
    const body = new FormData();
    body.append('file', file);

    const res = await api(`/api/v2/uploads/import?dataset=${dataset}`, { method: 'POST', body });
    const data = await res.json();
    if (!res.ok) {
        output.textContent = JSON.stringify(data, null, 2);
        toast(data.detail || 'Import failed');
        return;
    }

    output.textContent = JSON.stringify(data, null, 2);
    toast(`Imported ${data.inserted_rows} rows`);
    await bootstrap();
}

async function loadActivityLogs() {
    const res = await api('/api/v2/activity/logs?limit=60');
    const rows = await res.json();
    const body = document.getElementById('activityBody');
    if (!body) return;
    body.innerHTML = rows.map((row) => `
        <tr>
            <td>${row.action || '-'}</td>
            <td>${row.target_type || '-'} ${row.target_id || ''}</td>
            <td>${row.details || '-'}</td>
            <td>${row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</td>
        </tr>
    `).join('') || '<tr><td colspan="4">No logs</td></tr>';
}

async function loadUserManagement() {
    const [activeRes, pendingRes, blockedRes, rejectedRes, adminRes, superAdminRes] = await Promise.all([
        api('/api/users/status/active'),
        api('/api/users/status/pending'),
        api('/api/users/status/blocked'),
        api('/api/users/status/rejected'),
        api('/api/users/role/admin'),
        api('/api/users/role/super_admin'),
    ]);
    state.roleUsers.active = await activeRes.json();
    state.roleUsers.pending = await pendingRes.json();
    state.roleUsers.blocked = await blockedRes.json();
    state.roleUsers.rejected = await rejectedRes.json();
    const admins = await adminRes.json();
    const superAdmins = await superAdminRes.json();
    const adminMap = new Map();
    admins.forEach((user) => adminMap.set(user.id, user));
    superAdmins.forEach((user) => adminMap.set(user.id, { ...user, role: 'admin' }));
    state.roleUsers.admins = Array.from(adminMap.values());
    if (state.tab === 'users') {
        renderDashboard();
    }
}

async function bootstrap() {
    const [statsRes, reqRes, logRes] = await Promise.all([
        api('/api/v2/dashboard/stats'),
        api('/api/v2/access-requests'),
        api('/api/v2/uploads/logs?limit=20'),
    ]);
    state.stats = await statsRes.json();
    state.requests = await reqRes.json();
    state.logs = await logRes.json();
    renderDashboard();
}

function render() {
    if (!state.token) {
        renderLogin();
        return;
    }
    bootstrap().catch((err) => {
        toast(err.message || 'Initialization failed');
    });
}

render();
