/**
 * main.js — Tab Routing, Form Submissions & Dynamic Modals
 * National Unified Material Master Platform
 */

document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    // ── State ────────────────────────────────────────────────────────
    let currentUploadId = null;
    let currentRole = 'cpse_user';

    // ── DOM Refs ─────────────────────────────────────────────────────
    const tabBtns       = document.querySelectorAll('.tab-btn');
    const tabPanes      = document.querySelectorAll('.tab-pane');
    const roleDropdown  = document.getElementById('roleSelector');
    const fileInput     = document.getElementById('fileInput');
    const dropzone      = document.getElementById('dropzone');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // ── Tab Navigation ───────────────────────────────────────────────
    function switchTab(tabId) {
        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));

        const targetBtn = document.querySelector(`[data-tab="${tabId}"]`);
        const targetPane = document.getElementById(tabId);
        if (targetBtn) targetBtn.classList.add('active');
        if (targetPane) targetPane.classList.add('active');
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // ── Role Selector ────────────────────────────────────────────────
    if (roleDropdown) {
        roleDropdown.addEventListener('change', (e) => {
            currentRole = e.target.value;
            updateRoleVisibility();
            showToast(`Role switched to ${currentRole === 'super_admin' ? 'Super Admin (Ministry)' : 'CPSE User'}`, 'info');
        });
    }

    function updateRoleVisibility() {
        const adminEls = document.querySelectorAll('.admin-only');
        const cpseEls  = document.querySelectorAll('.cpse-only');
        adminEls.forEach(el => {
            el.style.display = currentRole === 'super_admin' ? '' : 'none';
        });
        cpseEls.forEach(el => {
            el.style.display = currentRole === 'cpse_user' ? '' : 'none';
        });
    }

    // ── Toast Notifications ──────────────────────────────────────────
    function showToast(message, type) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type || 'info'}`;
        const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }

    // ── Loading Overlay ──────────────────────────────────────────────
    function showLoading(msg) {
        if (!loadingOverlay) return;
        const p = loadingOverlay.querySelector('p');
        if (p) p.textContent = msg || 'Processing...';
        loadingOverlay.classList.add('active');
    }

    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.remove('active');
    }

    // ══════════════════════════════════════════════════════════════════
    // TAB 1: DATA INGESTION
    // ══════════════════════════════════════════════════════════════════

    // Drop zone interactions
    if (dropzone && fileInput) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-over');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleFileUpload(fileInput.files[0]);
            }
        });
    }

    async function handleFileUpload(file) {
        StreamingTerminal.init('extractionTerminal');
        StreamingTerminal.clear();
        StreamingTerminal.show();

        // Pre-processing logs
        await StreamingTerminal.writeLine(`[PROCESSING]: Received file '${file.name}' (${(file.size / 1024).toFixed(1)} KB)`, 200);
        await StreamingTerminal.writeLine(`[PROCESSING]: Parsing file format...`, 300);

        const formData = new FormData();
        formData.append('file', file);

        showLoading('Uploading & processing file...');

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();

            hideLoading();

            if (data.error) {
                await StreamingTerminal.writeLine(`[ERROR]: ${data.error}`, 100);
                showToast(data.error, 'error');
                return;
            }

            currentUploadId = data.upload_id;

            // Stream the logs
            if (data.logs && data.logs.length) {
                await StreamingTerminal.streamLogs(data.logs, 100);
            }

            // Render extracted data table
            renderExtractedData(data);

            // Update tab 1 badge
            const badge1 = document.getElementById('badge-tab1');
            if (badge1) badge1.textContent = data.total_rows;

            showToast(`Successfully ingested ${data.total_rows} records from ${file.name}`, 'success');

        } catch (err) {
            hideLoading();
            await StreamingTerminal.writeLine(`[ERROR]: Upload failed — ${err.message}`, 100);
            showToast('Upload failed. Please try again.', 'error');
        }
    }

    function renderExtractedData(data) {
        const container = document.getElementById('extractedDataContainer');
        if (!container || !data.data || data.data.length === 0) return;

        const headers = Object.keys(data.data[0]);

        let html = `
            <div class="data-table-container">
                <table class="data-table" id="extractedTable">
                    <thead><tr>
                        ${headers.map(h => `<th>${h.replace(/_/g, ' ')}</th>`).join('')}
                    </tr></thead>
                    <tbody id="extractedTableBody"></tbody>
                </table>
            </div>
        `;
        container.innerHTML = html;

        // Stream rows with animation
        StreamingTerminal.streamTableRows('extractedTableBody', data.data, (row) => {
            const tr = document.createElement('tr');
            headers.forEach(h => {
                const td = document.createElement('td');
                td.textContent = row[h] || '';
                td.title = row[h] || '';
                tr.appendChild(td);
            });
            return tr;
        }, 60);
    }

    // ══════════════════════════════════════════════════════════════════
    // TAB 2: AI MATCHING & APPROVAL
    // ══════════════════════════════════════════════════════════════════

    const runMatchBtn = document.getElementById('runMatchBtn');
    if (runMatchBtn) {
        runMatchBtn.addEventListener('click', runAIMatching);
    }

    async function runAIMatching() {
        if (!currentUploadId) {
            showToast('Please upload data in Tab 1 first.', 'warning');
            return;
        }

        showLoading('Running AI matching pipeline...');

        try {
            const res = await fetch('/api/match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ upload_id: currentUploadId }),
            });
            const data = await res.json();
            hideLoading();

            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            renderMatchResults(data);

            // Update badge
            const badge2 = document.getElementById('badge-tab2');
            if (badge2) badge2.textContent = data.total_clusters;

            showToast(`Found ${data.total_matches} duplicate pairs in ${data.total_clusters} clusters`, 'success');

        } catch (err) {
            hideLoading();
            showToast('Matching failed. ' + err.message, 'error');
        }
    }

    function renderMatchResults(data) {
        const container = document.getElementById('matchResultsContainer');
        if (!container) return;

        if (!data.clusters || data.clusters.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">🔍</span>
                    <h3>No Duplicates Found</h3>
                    <p>The AI engine did not find any matching duplicates above the 80% threshold.</p>
                </div>
            `;
            return;
        }

        let html = '';

        data.clusters.forEach((cluster, idx) => {
            const statusClass = cluster.status || 'pending';
            html += `
                <div class="match-card" id="cluster-${idx}">
                    <div class="match-card-header">
                        <div>
                            <span class="cnmc-code">${cluster.cnmc_code}</span>
                            <span class="status-badge ${statusClass}" id="status-${cluster.cnmc_code}">${statusClass}</span>
                        </div>
                        <div class="btn-group admin-only" style="${currentRole !== 'super_admin' ? 'display:none' : ''}">
                            <button class="btn btn-success btn-sm" onclick="approveCluster('${cluster.cnmc_code}', this)">✓ Approve</button>
                            <button class="btn btn-danger btn-sm" onclick="rejectCluster('${cluster.cnmc_code}', this)">✕ Reject</button>
                        </div>
                    </div>
                    <div class="match-members">
            `;

            cluster.members.forEach(member => {
                html += `
                        <div class="match-member-row">
                            <span class="cpse-tag">${member.cpse || 'N/A'}</span>
                            <span style="font-family:'Roboto Mono',monospace;font-size:0.78rem;color:var(--text-muted)">${member.local_code || '—'}</span>
                            <span style="flex:1">${member.description || ''}</span>
                            <span style="color:var(--text-muted);font-size:0.78rem">${member.uom || ''}</span>
                            <span style="font-weight:600">${member.qty || ''}</span>
                        </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        });

        // Show match score pairs above clusters
        if (data.matches && data.matches.length > 0) {
            let matchTable = `
                <div class="section-header" style="margin-top:0">
                    <div class="section-icon">🤖</div>
                    <h2>AI Match Scores</h2>
                </div>
                <div class="data-table-container" style="margin-bottom:24px">
                    <table class="data-table">
                        <thead><tr>
                            <th>CPSE A</th><th>Item A</th>
                            <th>CPSE B</th><th>Item B</th>
                            <th>Match Score</th>
                        </tr></thead>
                        <tbody>
            `;
            data.matches.forEach(m => {
                const scoreClass = m.score >= 92 ? 'high' : m.score >= 80 ? 'medium' : 'low';
                matchTable += `
                    <tr>
                        <td><span class="cpse-tag">${m.item_a.cpse || ''}</span></td>
                        <td title="${m.item_a.description}">${truncate(m.item_a.description, 60)}</td>
                        <td><span class="cpse-tag">${m.item_b.cpse || ''}</span></td>
                        <td title="${m.item_b.description}">${truncate(m.item_b.description, 60)}</td>
                        <td><span class="score-badge ${scoreClass}">${m.score}%</span></td>
                    </tr>
                `;
            });
            matchTable += `</tbody></table></div>`;
            html = matchTable + `
                <div class="section-header">
                    <div class="section-icon">📦</div>
                    <h2>Proposed National Clusters</h2>
                </div>
            ` + html;
        }

        container.innerHTML = html;
    }

    // Global approve/reject handlers
    window.approveCluster = async function(cnmcCode, btn) {
        try {
            const res = await fetch('/api/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cnmc_code: cnmcCode,
                    action: 'approve',
                    reviewer: 'Super Admin',
                }),
            });
            const data = await res.json();
            if (data.error) { showToast(data.error, 'error'); return; }

            const badge = document.getElementById(`status-${cnmcCode}`);
            if (badge) {
                badge.className = 'status-badge approved';
                badge.textContent = 'approved';
            }
            showToast(`${cnmcCode} approved successfully`, 'success');
        } catch (e) {
            showToast('Approval failed', 'error');
        }
    };

    window.rejectCluster = async function(cnmcCode, btn) {
        try {
            const res = await fetch('/api/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cnmc_code: cnmcCode,
                    action: 'reject',
                    reviewer: 'Super Admin',
                }),
            });
            const data = await res.json();
            if (data.error) { showToast(data.error, 'error'); return; }

            const badge = document.getElementById(`status-${cnmcCode}`);
            if (badge) {
                badge.className = 'status-badge rejected';
                badge.textContent = 'rejected';
            }
            showToast(`${cnmcCode} rejected`, 'warning');
        } catch (e) {
            showToast('Rejection failed', 'error');
        }
    };

    // ══════════════════════════════════════════════════════════════════
    // TAB 3: SEARCH & INVENTORY
    // ══════════════════════════════════════════════════════════════════

    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    // Also search on Enter key
    const searchInput = document.getElementById('searchQuery');
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    async function performSearch() {
        const query = document.getElementById('searchQuery')?.value?.trim();
        const searchType = document.getElementById('searchType')?.value || 'description';

        if (!query) {
            showToast('Please enter a search query.', 'warning');
            return;
        }

        showLoading('Searching across all CPSEs...');

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, search_type: searchType }),
            });
            const data = await res.json();
            hideLoading();

            renderSearchResults(data);

        } catch (err) {
            hideLoading();
            showToast('Search failed.', 'error');
        }
    }

    function renderSearchResults(data) {
        const container = document.getElementById('searchResultsContainer');
        if (!container) return;

        if (!data.results || data.results.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">🔍</span>
                    <h3>No Results Found</h3>
                    <p>No materials matched your query "${data.query}". Try a different search term.</p>
                </div>
            `;
            return;
        }

        // Determine columns from first result
        const keys = Object.keys(data.results[0]).filter(k => !k.startsWith('_'));
        let html = `
            <p style="margin-bottom:12px;color:var(--text-secondary);font-size:0.88rem">
                Found <strong>${data.total_results}</strong> result(s) for "<em>${data.query}</em>"
            </p>
            <div class="data-table-container">
                <table class="data-table">
                    <thead><tr>
                        ${keys.map(k => `<th>${k.replace(/_/g, ' ')}</th>`).join('')}
                    </tr></thead>
                    <tbody>
                        ${data.results.map(row => `
                            <tr>${keys.map(k => `<td title="${row[k] || ''}">${row[k] || '—'}</td>`).join('')}</tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.innerHTML = html;
    }

    // ══════════════════════════════════════════════════════════════════
    // TAB 4: ANALYTICS & DEMAND AGGREGATION
    // ══════════════════════════════════════════════════════════════════

    const refreshAnalyticsBtn = document.getElementById('refreshAnalyticsBtn');
    if (refreshAnalyticsBtn) {
        refreshAnalyticsBtn.addEventListener('click', loadAnalytics);
    }

    async function loadAnalytics() {
        try {
            const res = await fetch('/api/analytics');
            const data = await res.json();
            renderAnalytics(data);
        } catch (err) {
            showToast('Failed to load analytics.', 'error');
        }
    }

    function renderAnalytics(data) {
        // Update stat cards
        setStatValue('statTotalMaterials', data.total_materials);
        setStatValue('statTotalCPSEs', data.total_cpses);
        setStatValue('statTotalClusters', data.total_clusters);
        setStatValue('statApproved', data.approved_clusters);
        setStatValue('statDuplicatePairs', data.total_duplicate_pairs);
        setStatValue('statDupReduced', data.duplicates_reduced_pct + '%');

        // Render CPSE bar chart
        renderBarChart('cpseMaterialChart', data.cpse_material_counts, 'Materials per CPSE');

        // Render category bar chart
        renderBarChart('categoryChart', data.category_breakdown, 'Clusters by Category');

        // Render donut/ring for approval status
        renderApprovalRing(data);

        // Render demand aggregation table
        renderDemandTable(data.demand_aggregation);
    }

    function setStatValue(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? 0;
    }

    function renderBarChart(containerId, dataObj, title) {
        const container = document.getElementById(containerId);
        if (!container || !dataObj) return;

        const entries = Object.entries(dataObj);
        if (entries.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding:30px"><span class="empty-icon">📊</span><p>No data available yet.</p></div>`;
            return;
        }

        const maxVal = Math.max(...entries.map(e => e[1]));
        const colors = ['navy', 'saffron', 'green'];

        let html = `<div class="bar-chart">`;
        entries.forEach(([label, value], i) => {
            const heightPct = maxVal > 0 ? (value / maxVal) * 200 : 0;
            const color = colors[i % colors.length];
            html += `
                <div class="bar-col">
                    <span class="bar-value">${value}</span>
                    <div class="bar-fill ${color}" style="height:${heightPct}px"></div>
                    <span class="bar-label" title="${label}">${label}</span>
                </div>
            `;
        });
        html += `</div>`;
        container.innerHTML = html;
    }

    function renderApprovalRing(data) {
        const container = document.getElementById('approvalRing');
        if (!container) return;

        const total = data.total_clusters || 0;
        const approved = data.approved_clusters || 0;
        const pct = total > 0 ? Math.round((approved / total) * 100) : 0;

        const circumference = 2 * Math.PI * 60;
        const offset = circumference - (pct / 100) * circumference;

        container.innerHTML = `
            <div class="metric-ring">
                <svg width="160" height="160" viewBox="0 0 160 160">
                    <circle class="ring-bg" cx="80" cy="80" r="60"/>
                    <circle class="ring-fill" cx="80" cy="80" r="60"
                        stroke="var(--green-india)"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${offset}"/>
                </svg>
                <div class="ring-center">
                    <div class="ring-value">${pct}%</div>
                    <div class="ring-label">Approved</div>
                </div>
            </div>
            <div style="text-align:center;font-size:0.82rem;color:var(--text-muted)">
                ${approved} of ${total} clusters approved
            </div>
        `;
    }

    function renderDemandTable(aggregation) {
        const container = document.getElementById('demandAggregationContainer');
        if (!container) return;

        if (!aggregation || aggregation.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📦</span>
                    <h3>No Aggregated Demand Data</h3>
                    <p>Approve some clusters in Tab 2 to see demand aggregation here.</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="data-table-container">
                <table class="data-table">
                    <thead><tr>
                        <th>CNMC Code</th>
                        <th>Category</th>
                        <th>Total Quantity</th>
                        <th>Members</th>
                        <th>CPSE Breakdown</th>
                    </tr></thead>
                    <tbody>
        `;

        aggregation.forEach(item => {
            const cpseChips = Object.entries(item.cpse_breakdown || {}).map(([cpse, qty]) =>
                `<span class="demand-cpse-chip"><strong>${cpse}</strong>: ${qty}</span>`
            ).join('');

            html += `
                <tr>
                    <td><span class="cnmc-code">${item.cnmc_code}</span></td>
                    <td>${item.category}</td>
                    <td style="font-weight:700">${item.total_quantity}</td>
                    <td>${item.member_count}</td>
                    <td><div class="demand-row-cpse">${cpseChips || '—'}</div></td>
                </tr>
            `;
        });

        html += `</tbody></table></div>`;
        container.innerHTML = html;
    }

    // ── Utility ──────────────────────────────────────────────────────

    function truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    }

    // ── Initialize ───────────────────────────────────────────────────
    updateRoleVisibility();
    switchTab('tab-ingest');
});
