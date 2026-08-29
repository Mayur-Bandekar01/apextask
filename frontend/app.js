/**
 * APEXTASK — ULTIMATE TO-DO LIST WEB APPLICATION JAVASCRIPT
 * Full-Stack REST Client, Single-User JWT Authentication, Web Audio Synthesizer,
 * Confetti Engine, Analytics & Gamification
 */

// ==================== CONFIGURATION & STATE ====================
const API_BASE = '/api';

const state = {
    user: null,
    tasks: [],
    missedTasks: [],
    currentTab: 'today',
    currentFilter: 'all',
    searchQuery: '',
    soundEnabled: true,
    activeWeeklyDate: 'today',
    activeMonthlyDate: null,
    activeYearlyDate: null,
    yearlyChart: null,
    dateTasksModalData: null,
    taskToDeleteId: null
// ==================== API QUEUE & LOADING / ANIMATION HELPERS ====================
class APIQueue {
    constructor() {
        this.queue = Promise.resolve();
    }
    enqueue(fn) {
        this.queue = this.queue.then(fn).catch(err => {
            console.error('[APIQueue Error]', err);
        });
        return this.queue;
    }
}
const apiQueue = new APIQueue();

function showGlobalLoading(statusText = 'Synchronizing with cloud...') {
    const overlay = document.getElementById('global-loading-overlay');
    const textEl = document.getElementById('loading-status-text');
    if (!overlay) return;
    if (textEl) textEl.textContent = statusText;
    overlay.classList.remove('hidden', 'fade-out');
}

function hideGlobalLoading() {
    const overlay = document.getElementById('global-loading-overlay');
    if (!overlay) return;
    overlay.classList.add('fade-out');
    setTimeout(() => {
        overlay.classList.add('hidden');
        overlay.classList.remove('fade-out');
    }, 200);
}

function triggerParticleBurst(x, y) {
    const container = document.createElement('div');
    container.className = 'burst-particle-container';
    container.style.left = `${x || window.innerWidth / 2}px`;
    container.style.top = `${y || window.innerHeight / 2}px`;

    const colors = ['#7c3aed', '#fbbf24', '#10b981', '#ec4899', '#38bdf8', '#a855f7', '#f59e0b', '#ef4444'];
    const angles = [0, 45, 90, 135, 180, 225, 270, 315];

    angles.forEach((angle, i) => {
        const p = document.createElement('div');
        p.className = 'burst-particle';
        p.style.backgroundColor = colors[i % colors.length];

        const distance = 40 + Math.random() * 25;
        const rad = (angle * Math.PI) / 180;
        const tx = Math.cos(rad) * distance;
        const ty = Math.sin(rad) * distance;

        p.style.setProperty('--tx', `${tx}px`);
        p.style.setProperty('--ty', `${ty}px`);
        container.appendChild(p);
    });

    document.body.appendChild(container);
    setTimeout(() => container.remove(), 600);
}

function animateMilestoneWipe() {
    const fill = document.getElementById('xp-bar-fill') || document.querySelector('.xp-progress-bar-fill');
    if (!fill) return;
    fill.classList.add('milestone-bar-wipe');
    setTimeout(() => fill.classList.remove('milestone-bar-wipe'), 450);
}

function animateXpCounter(fromXp, toXp, duration = 800) {
    const xpCurrEl = document.getElementById('xp-current');
    if (!xpCurrEl) return;

    const start = performance.now();
    const diff = toXp - fromXp;

    function step(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(fromXp + diff * progress);
        xpCurrEl.textContent = current.toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            xpCurrEl.textContent = toXp.toLocaleString();
        }
    }
    requestAnimationFrame(step);
}

function renderSkeletonCards(containerId = 'today-tasks-list', count = 4) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="skeleton-task-card">
                <div class="skeleton-shimmer skeleton-title-bar"></div>
                <div class="skeleton-shimmer skeleton-notes-bar"></div>
                <div class="skeleton-pills-row">
                    <div class="skeleton-shimmer skeleton-pill-box"></div>
                    <div class="skeleton-shimmer skeleton-pill-box"></div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

// ==================== AUTH GUARD & HELPERS ====================
function getAuthToken() {
    return sessionStorage.getItem('apextask_token');
}

function handleLogout() {
    sessionStorage.removeItem('apextask_token');
    sessionStorage.removeItem('apextask_user');
    window.location.href = '/';
}

async function verifyAuthentication() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/';
        return false;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!res.ok) {
            handleLogout();
            return false;
        }

        const data = await res.json();
        if (data.valid && data.profile) {
            state.user = data.profile;
            return true;
        } else {
            handleLogout();
            return false;
        }
    } catch (e) {
        console.error('Auth verification error:', e);
        handleLogout();
        return false;
    }
}

// ==================== WEB AUDIO SYNTHESIZER ====================
class SoundFX {
    constructor() {
        this.ctx = null;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    play(type) {
        if (!state.soundEnabled) return;
        try {
            this.init();
            if (!this.ctx) return;

            const now = this.ctx.currentTime;

            if (type === 'complete') {
                // Harmonious crisp bell chime (C5 -> E5 -> G5)
                const notes = [523.25, 659.25, 783.99];
                notes.forEach((freq, i) => {
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, now + i * 0.07);

                    gain.gain.setValueAtTime(0.2, now + i * 0.07);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.07 + 0.35);

                    osc.connect(gain);
                    gain.connect(this.ctx.destination);

                    osc.start(now + i * 0.07);
                    osc.stop(now + i * 0.07 + 0.35);
                });
            } else if (type === 'levelup') {
                // Triumphant RPG Fanfare
                const notes = [440, 554.37, 659.25, 880, 1108.73];
                notes.forEach((freq, i) => {
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(freq, now + i * 0.08);

                    gain.gain.setValueAtTime(0.25, now + i * 0.08);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.5);

                    osc.connect(gain);
                    gain.connect(this.ctx.destination);

                    osc.start(now + i * 0.08);
                    osc.stop(now + i * 0.08 + 0.5);
                });
            } else if (type === 'chest') {
                // Magical shimmering chord
                const freqs = [587.33, 739.99, 880, 1174.66, 1479.98];
                freqs.forEach((freq, idx) => {
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, now + idx * 0.05);

                    gain.gain.setValueAtTime(0.18, now + idx * 0.05);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.05 + 0.6);

                    osc.connect(gain);
                    gain.connect(this.ctx.destination);

                    osc.start(now + idx * 0.05);
                    osc.stop(now + idx * 0.05 + 0.6);
                });
            } else if (type === 'streak_loss') {
                // Low descending alert buzzer
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(180, now);
                osc.frequency.exponentialRampToValueAtTime(80, now + 0.35);

                gain.gain.setValueAtTime(0.2, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(now);
                osc.stop(now + 0.35);
            } else if (type === 'click') {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(800, now);
                gain.gain.setValueAtTime(0.05, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.start(now);
                osc.stop(now + 0.05);
            }
        } catch (e) {
            console.warn('Audio synthesis error:', e);
        }
    }
}

const audio = new SoundFX();

// Ambient Top Loading Progress Bar Controller
let loadingBarTimer = null;
function startTopLoadingBar() {
    const bar = document.getElementById('top-loading-bar');
    if (!bar) return;
    if (loadingBarTimer) clearInterval(loadingBarTimer);
    bar.style.opacity = '1';
    bar.style.width = '15%';

    let currentWidth = 15;
    loadingBarTimer = setInterval(() => {
        if (currentWidth < 85) {
            currentWidth += Math.random() * 15;
            bar.style.width = `${currentWidth}%`;
        }
    }, 180);
}

function finishTopLoadingBar() {
    const bar = document.getElementById('top-loading-bar');
    if (!bar) return;
    if (loadingBarTimer) clearInterval(loadingBarTimer);
    bar.style.width = '100%';
    setTimeout(() => {
        bar.style.opacity = '0';
        setTimeout(() => {
            bar.style.width = '0%';
        }, 300);
    }, 200);
}

// ==================== REST API CLIENT WITH JWT ====================
async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const token = getAuthToken();
    startTopLoadingBar();

    try {
        const fetchOpts = { ...options };
        const method = (fetchOpts.method || 'GET').toUpperCase();

        const headers = {
            'Authorization': `Bearer ${token || ''}`,
            ...fetchOpts.headers
        };

        if (method !== 'GET' && method !== 'HEAD') {
            headers['Content-Type'] = 'application/json';
            if (fetchOpts.body === undefined) {
                fetchOpts.body = JSON.stringify({});
            }
        }

        fetchOpts.headers = headers;

        const res = await fetch(url, fetchOpts);

        if (res.status === 401) {
            handleLogout();
            throw new Error('Session expired. Please log in again.');
        }

        const contentType = res.headers.get('content-type') || '';
        
        let data;
        if (contentType.includes('application/json')) {
            data = await res.json();
        } else {
            const text = await res.text();
            throw new Error(`Server returned unexpected response (${res.status})`);
        }

        if (!res.ok) {
            throw new Error(data.error || `HTTP error ${res.status}`);
        }
        return data;
    } catch (err) {
        console.error(`[API Error] ${endpoint}:`, err);
        throw err;
    } finally {
        finishTopLoadingBar();
    }
}

// ==================== TOAST NOTIFICATIONS ====================
function showToast(message, type = 'info', icon = null) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;

    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'warning') iconClass = 'fa-triangle-exclamation';
    if (type === 'danger') iconClass = 'fa-circle-xmark';
    if (icon) iconClass = icon;

    toast.innerHTML = `
        <i class="fa-solid ${iconClass}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ==================== CELEBRATION CONFETTI ====================
function launchConfetti(type = 'default') {
    if (typeof confetti !== 'function') return;

    if (type === 'golden') {
        confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#fbbf24', '#f59e0b', '#d97706', '#ffffff']
        });
    } else if (type === 'levelup') {
        const count = 150;
        const defaults = { origin: { y: 0.7 } };
        function fire(particleRatio, opts) {
            confetti({
                ...defaults,
                ...opts,
                particleCount: Math.floor(count * particleRatio)
            });
        }
        fire(0.25, { spread: 26, startVelocity: 55, colors: ['#6366f1', '#a855f7', '#38bdf8'] });
        fire(0.2, { spread: 60, colors: ['#fbbf24', '#ec4899'] });
        fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8 });
        fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 });
        fire(0.1, { spread: 120, startVelocity: 45 });
    } else {
        confetti({
            particleCount: 50,
            spread: 60,
            origin: { y: 0.7 },
            colors: ['#6366f1', '#a855f7', '#10b981', '#38bdf8']
        });
    }
}

// ==================== PROFILE & GAMIFICATION RENDERER ====================
async function loadUserProfile() {
    try {
        const data = await api('/user/profile');
        if (data.success && data.profile) {
            state.user = data.profile;
            renderGamificationHeader();
        }
    } catch (e) {
        console.error('Failed to load profile:', e);
    }
}

function renderGamificationHeader() {
    const u = state.user;
    if (!u) return;

    // Database Engine Badge
    const dbBadge = document.getElementById('db-engine-badge');
    if (dbBadge) {
        const engineLabel = (u.db_engine || 'MySQL').toUpperCase();
        dbBadge.innerHTML = `<i class="fa-solid fa-database"></i> ${engineLabel === 'MYSQL' ? 'Cloud MySQL' : 'SQLite DB'}`;
    }

    // Title
    const titleEl = document.getElementById('user-title-text');
    if (titleEl) titleEl.textContent = u.title || 'Productivity Architect';

    // Slacker / Level at Risk Warning
    const riskEl = document.getElementById('level-risk-warning');
    if (riskEl) {
        if (u.level_at_risk || u.title === '😴 Slacker Mode') {
            riskEl.classList.remove('hidden');
        } else {
            riskEl.classList.add('hidden');
        }
    }

    // Level & XP Bar
    const lvlEl = document.getElementById('user-level');
    if (lvlEl) lvlEl.textContent = u.level || 1;

    const xpCurrEl = document.getElementById('xp-current');
    if (xpCurrEl) xpCurrEl.textContent = u.current_level_xp || 0;

    const xpTargetEl = document.getElementById('xp-target');
    if (xpTargetEl) xpTargetEl.textContent = u.needed_for_next || 100;

    const xpPercentEl = document.getElementById('xp-percent');
    if (xpPercentEl) xpPercentEl.textContent = `(${u.progress_percent || 0}%)`;

    const xpFillEl = document.getElementById('xp-bar-fill');
    if (xpFillEl) xpFillEl.style.width = `${Math.min(100, Math.max(0, u.progress_percent || 0))}%`;

    // Streak
    const streakCountEl = document.getElementById('streak-count');
    if (streakCountEl) streakCountEl.textContent = u.streak || 0;

    // Badges count badge on tab
    const badgeUnlockedTab = document.getElementById('badge-unlocked-count');
    if (badgeUnlockedTab) badgeUnlockedTab.textContent = u.badge_count || 0;

    // Mystery Chest tracker (Progress toward 10 tasks)
    const chestProgressText = document.getElementById('chest-progress-text');
    const chestWidget = document.getElementById('chest-widget');
    const totalComp = u.total_completed || 0;
    const currentProgress = totalComp % 10;
    
    if (chestProgressText) {
        chestProgressText.textContent = `${currentProgress}/10`;
    }

    if (chestWidget) {
        if (totalComp > 0 && currentProgress === 0) {
            chestWidget.classList.add('ready');
            chestWidget.setAttribute('title', 'Mystery Chest READY! Click to claim reward!');
        } else {
            chestWidget.classList.remove('ready');
            chestWidget.setAttribute('title', `Mystery Chest unlocks every 10 tasks (${10 - currentProgress} more to go)`);
        }
    }
}

// ==================== TASKS MODULE (TODAY & DRILLDOWN) ====================
async function loadTodayTasks() {
    renderSkeletonCards('today-tasks-list', 4);
    try {
        const data = await api('/tasks/today');
        if (data.success) {
            state.tasks = data.tasks || [];
            renderTodayTasks();
            updateTabBadges();
        }
    } catch (e) {
        console.error('Failed to load tasks:', e);
    }
}

function updateTabBadges() {
    const todayBadge = document.getElementById('badge-today-count');
    if (todayBadge) {
        const pendingCount = (state.tasks || []).filter(t => t.status === 'pending').length;
        todayBadge.textContent = pendingCount;
    }

    const missedBadge = document.getElementById('badge-missed-count');
    if (missedBadge) {
        const missedCount = (state.missedTasks || []).length;
        missedBadge.textContent = missedCount;
        if (missedCount > 0) {
            missedBadge.classList.remove('hidden');
        } else {
            missedBadge.classList.add('hidden');
        }
    }

    const challengeBadge = document.getElementById('badge-challenges-count');
    if (challengeBadge) {
        challengeBadge.classList.add('hidden');
        challengeBadge.textContent = '';
    }
}

// ==================== PURE VANILLA JS LEVENSHTEIN FUZZY SEARCH ====================
function levenshteinDistance(s1, s2) {
    if (!s1 || !s2) return (s1 || s2 || '').length;
    s1 = s1.toLowerCase();
    s2 = s2.toLowerCase();
    const costs = [];
    for (let i = 0; i <= s1.length; i++) {
        let lastValue = i;
        for (let j = 0; j <= s2.length; j++) {
            if (i === 0) costs[j] = j;
            else if (j > 0) {
                let newValue = costs[j - 1];
                if (s1.charAt(i - 1) !== s2.charAt(j - 1))
                    newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                costs[j - 1] = lastValue;
                lastValue = newValue;
            }
        }
        if (i > 0) costs[s2.length] = lastValue;
    }
    return costs[s2.length];
}

function fuzzyMatch(text, query) {
    if (!query) return true;
    if (!text) return false;
    text = text.toLowerCase();
    query = query.toLowerCase().trim();
    if (text.includes(query)) return true;
    
    // Test fuzzy distance against split tokens
    const words = text.split(/[\s,#_-]+/);
    for (const w of words) {
        if (!w) continue;
        if (w.includes(query) || query.includes(w)) return true;
        const maxDist = query.length <= 3 ? 1 : 2;
        if (levenshteinDistance(w, query) <= maxDist) return true;
    }
    return false;
}

function renderTodayTasks() {
    const listContainer = document.getElementById('today-task-list');
    const emptyState = document.getElementById('today-empty-state');
    if (!listContainer) return;

    // Filter tasks
    let filtered = state.tasks.filter(t => {
        // Tab filter
        if (state.currentFilter === 'pending' && t.status !== 'pending') return false;
        if (state.currentFilter === 'complete' && t.status !== 'complete') return false;
        if (state.currentFilter === 'boss' && !t.is_boss) return false;
        if (state.currentFilter === 'high' && (t.priority || '').toLowerCase() !== 'high') return false;
        if (state.currentFilter === 'rolled' && (t.rollover_count || 0) === 0) return false;

        // Levenshtein Real-Time Fuzzy Search across title, notes, and tags
        if (state.searchQuery.trim()) {
            const q = state.searchQuery.trim();
            const titleMatch = fuzzyMatch(t.title, q);
            const notesMatch = fuzzyMatch(t.notes, q);
            const tagsMatch = fuzzyMatch(t.tags, q);
            if (!titleMatch && !notesMatch && !tagsMatch) return false;
        }

        return true;
    });

    if (filtered.length === 0) {
        listContainer.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    listContainer.innerHTML = filtered.map(t => createTaskCardHTML(t)).join('');
}

function createTaskCardHTML(t) {
    const isComplete = t.status === 'complete';
    const isRolled = (t.rollover_count || 0) > 0;
    const daysPending = t.days_pending || 0;
    const isBoss = Boolean(t.is_boss);

    // Determine pending glow level
    let glowClass = '';
    if (!isComplete) {
        if (daysPending >= 3) glowClass = 'glow-pending-3';
        else if (daysPending >= 2) glowClass = 'glow-pending-2';
        else if (daysPending >= 1) glowClass = 'glow-pending-1';
    }

    // Format deadline
    let deadlineHTML = '';
    if (t.deadline) {
        const deadlineDate = new Date(t.deadline);
        const isOverdue = !isComplete && deadlineDate < new Date();
        const formatted = deadlineDate.toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        deadlineHTML = `
            <div class="task-deadline ${isOverdue ? 'is-overdue' : ''}">
                <i class="fa-regular fa-clock"></i>
                <span>${isOverdue ? '⚠️ Overdue: ' : 'Due: '}${formatted}</span>
            </div>
        `;
    }

    // Tags
    let tagsHTML = '';
    if (t.tags) {
        const tagList = t.tags.split(/[\s,]+/).filter(Boolean);
        if (tagList.length > 0) {
            tagsHTML = tagList.map(tag => `<span class="tag-pill">${escapeHTML(tag.startsWith('#') ? tag : '#' + tag)}</span>`).join('');
        }
    }

    // Subtasks Checklist
    let subtasksHTML = '';
    if (Array.isArray(t.subtasks) && t.subtasks.length > 0) {
        subtasksHTML = `
            <div class="task-card-subtasks">
                ${t.subtasks.map((st, idx) => {
                    const isDone = Boolean(st.is_done || st.completed);
                    return `
                        <label class="card-subtask-item ${isDone ? 'is-done' : ''}" onclick="event.stopPropagation(); handleSubtaskToggle(${t.id}, ${idx})">
                            <input type="checkbox" class="card-subtask-check" ${isDone ? 'checked' : ''} onclick="event.stopPropagation()">
                            <span>${escapeHTML(st.title)}</span>
                        </label>
                    `;
                }).join('')}
            </div>
        `;
    }

    return `
        <div class="task-card ${isComplete ? 'is-complete' : ''} ${isRolled ? 'is-rolled-over' : ''} ${glowClass}" data-task-id="${t.id}">
            <div class="task-card-header">
                <button class="task-check-btn" title="${isComplete ? 'Mark Incomplete' : 'Mark Complete'}" data-action="toggle-complete">
                    <i class="fa-solid fa-check"></i>
                </button>

                <div class="task-main-info">
                    <div class="task-title">${escapeHTML(t.title)}</div>
                    ${t.notes ? `<div class="task-notes">${escapeHTML(t.notes)}</div>` : ''}

                    ${subtasksHTML}

                    <div class="task-tags-row">
                        <span class="priority-tag priority-${t.priority || 'medium'}">${t.priority || 'medium'}</span>
                        ${tagsHTML}
                        
                        ${isRolled ? `
                            <span class="rollover-tag" title="Auto-rolled over from previous day">
                                <i class="fa-solid fa-arrows-rotate"></i> Rolled Over (${t.rollover_count})
                            </span>
                        ` : ''}

                        ${(!isComplete && daysPending > 0) ? `
                            <span class="pending-chain-tag" title="Original Date: ${t.original_date}">
                                <i class="fa-solid fa-hourglass-half"></i> Pending for ${daysPending} ${daysPending === 1 ? 'day' : 'days'}
                            </span>
                        ` : ''}
                    </div>
                </div>
            </div>

            <div class="task-card-footer">
                ${deadlineHTML || '<div class="task-deadline"><i class="fa-regular fa-calendar"></i> ' + (t.original_date || 'Today') + '</div>'}

                <div class="task-actions">
                    <button class="btn-action" data-action="view-logs" title="View Lifecycle History (${t.log_count || 0} logs)">
                        <i class="fa-solid fa-timeline"></i>
                    </button>
                    <button class="btn-action" data-action="edit-task" title="Edit Task">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button class="btn-action delete-btn" data-action="delete-task" title="Delete Task">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ==================== TASK ACTIONS ====================
async function handleToggleComplete(taskId) {
    const checkBtn = document.querySelector(`[data-task-id="${taskId}"] .task-check-btn`);
    if (checkBtn) {
        checkBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size:12px;color:var(--primary);"></i>';
        checkBtn.style.pointerEvents = 'none';
    }

    try {
        const res = await api(`/tasks/${taskId}/complete`, { method: 'PUT' });
        if (res.success && res.result) {
            const r = res.result;

            if (r.status === 'complete') {
                audio.play('complete');
                const isLevelUp = r.xp_result && r.xp_result.leveled_up;
                launchConfetti(isLevelUp ? 'levelup' : 'default');

                const bossMsg = r.is_boss ? ' 👑 3X BOSS BOUNTY CLAIMED!' : '';
                showToast(`Task completed! +${r.xp_delta} XP earned 🔥${bossMsg}`, 'success');

                if (isLevelUp) {
                    triggerLevelUp(r.xp_result.level, r.profile ? r.profile.title : null);
                }

                if (r.new_badges && r.new_badges.length > 0) {
                    r.new_badges.forEach(b => {
                        setTimeout(() => {
                            audio.play('chest');
                            showToast(`🏆 Badge Unlocked: ${b.title}!`, 'warning', 'fa-award');
                        }, 800);
                    });
                }
            } else {
                audio.play('click');
                showToast(`Task reopened (${r.xp_delta} XP)`, 'info');
            }

            if (r.streak_lost) {
                audio.play('streak_loss');
                showToast('⚠️ Streak Lost! Keep going to rebuild momentum.', 'danger');
            }

            if (r.profile) {
                state.user = r.profile;
                renderGamificationHeader();
            }

            await loadTodayTasks();
            await loadUserProfile();
            updateTabBadges();
            if (state.currentTab === 'weekly') loadWeeklyDashboard();
            if (state.currentTab === 'monthly') loadMonthlyDashboard();
            if (state.currentTab === 'yearly') loadYearlyDashboard();
            if (state.currentTab === 'shame') loadShameBoard();
            if (state.currentTab === 'badges') loadBadgesShowcase();
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// Boss Battle Strike Handler
async function handleBossDamage(taskId, subtaskIndex) {
    try {
        const res = await api(`/tasks/${taskId}/boss/damage`, {
            method: 'POST',
            body: JSON.stringify({ subtask_index: subtaskIndex })
        });

        if (res.success && res.result) {
            const r = res.result;
            audio.play('complete');

            if (r.is_defeated) {
                audio.play('levelup');
                launchConfetti('golden');
                showToast('💥 BOSS DEFEATED! 3x XP multiplier claimed & Mystery Chest ready!', 'success', 'fa-crown');
                setTimeout(() => openRewardChestModal(), 1200);
            } else {
                showToast(`⚔️ Direct Strike! Boss HP: ${r.boss_hp}/100 (+${r.xp_awarded} XP)`, 'warning');
            }

            if (r.xp_result && r.xp_result.leveled_up) {
                triggerLevelUp(r.xp_result.level, r.profile ? r.profile.title : null);
            }

            if (r.profile) {
                state.user = r.profile;
                renderGamificationHeader();
            }

            await loadTodayTasks();
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// Level Up Celebration Modal
function triggerLevelUp(level, title) {
    const modal = document.getElementById('levelup-modal-backdrop');
    if (!modal) return;

    const levelEl = document.getElementById('levelup-modal-level');
    const titleEl = document.getElementById('levelup-modal-title');
    if (levelEl) levelEl.textContent = level;
    if (titleEl && title) titleEl.textContent = title;

    modal.classList.remove('hidden');
    audio.play('levelup');
    launchConfetti('levelup');

    const halo = document.getElementById('levelup-badge-halo');
    if (halo && halo.animate) {
        halo.animate([
            { transform: 'scale(0.5) rotate(-20deg)', opacity: 0 },
            { transform: 'scale(1.2) rotate(10deg)', opacity: 1 },
            { transform: 'scale(1.0) rotate(0deg)', opacity: 1 }
        ], {
            duration: 700,
            easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)'
        });
    }
}

// In-App Delete Confirmation Modal logic
function openDeleteConfirmModal(taskId) {
    state.taskToDeleteId = taskId;
    const task = state.tasks.find(t => t.id === taskId) || state.missedTasks.find(t => t.id === taskId);
    const deleteModal = document.getElementById('delete-modal-backdrop');
    const deleteText = document.getElementById('delete-modal-text');

    if (deleteText && task) {
        deleteText.innerHTML = `Are you sure you want to permanently delete <strong>"${escapeHTML(task.title)}"</strong>?`;
    }
    if (deleteModal) {
        deleteModal.classList.remove('hidden');
    }
}

function closeDeleteConfirmModal() {
    state.taskToDeleteId = null;
    const deleteModal = document.getElementById('delete-modal-backdrop');
    if (deleteModal) {
        deleteModal.classList.add('hidden');
    }
}

async function confirmDeleteTask() {
    const taskId = state.taskToDeleteId;
    if (!taskId) return;

    const btnConfirm = document.getElementById('btn-confirm-delete');
    const originalText = btnConfirm ? btnConfirm.innerHTML : 'Delete';

    // Highlight target task card with deleting state immediately
    const card = document.querySelector(`[data-task-id="${taskId}"]`);
    if (card) card.classList.add('is-deleting');

    if (btnConfirm) {
        btnConfirm.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting Mission...';
        btnConfirm.disabled = true;
    }

    try {
        const res = await api(`/tasks/${taskId}`, { method: 'DELETE' });
        if (res.success) {
            audio.play('click');
            showToast('Mission deleted successfully', 'info');
            closeDeleteConfirmModal();
            await loadTodayTasks();
            await loadUserProfile();
            updateTabBadges();
            if (state.currentTab === 'shame') loadShameBoard();
            if (state.currentTab === 'weekly') loadWeeklyDashboard();
            if (state.currentTab === 'monthly') loadMonthlyDashboard();
            if (state.currentTab === 'yearly') loadYearlyDashboard();
        }
    } catch (e) {
        showToast(e.message, 'danger');
        if (card) card.classList.remove('is-deleting');
        closeDeleteConfirmModal();
    } finally {
        if (btnConfirm) {
            btnConfirm.innerHTML = originalText;
            btnConfirm.disabled = false;
        }
    }
}

async function triggerAutoRollover(manual = false) {
    try {
        const res = await api('/tasks/rollover', { method: 'POST' });
        if (res.success && res.rollover) {
            const count = res.rollover.rolled_count || 0;
            if (count > 0) {
                showToast(`🔁 Rolled over ${count} pending task${count > 1 ? 's' : ''} to today!`, 'warning');
                await loadTodayTasks();
            } else if (manual) {
                showToast('All tasks are up to date. No pending rollovers.', 'info');
            }
        }
    } catch (e) {
        if (manual) showToast(e.message, 'danger');
    }
}

// ==================== SUBTASK HELPER & MODAL INITIALIZATION ====================
let bossListenerAttached = false;

function createSubtaskRow(title = '', isDone = false) {
    const list = document.getElementById('subtask-list');
    if (!list) return;

    const row = document.createElement('div');
    row.className = 'subtask-row';
    row.innerHTML = `
        <input type="checkbox" class="subtask-row-check" ${isDone ? 'checked' : ''}>
        <input type="text" class="form-control subtask-row-title" placeholder="Subtask title..." value="${escapeHTML(title)}">
        <button type="button" class="btn-remove-subtask" title="Remove subtask">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    const removeBtn = row.querySelector('.btn-remove-subtask');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            row.remove();
        });
    }

    list.appendChild(row);
}

async function handleSubtaskToggle(taskId, subtaskIndex) {
    try {
        startTopLoadingBar();
        const res = await api(`/tasks/${taskId}/subtasks/${subtaskIndex}/toggle`, {
            method: 'POST'
        });
        if (res.success) {
            audio.play('click');
            await loadTodayTasks();
            if (state.currentTab === 'weekly') loadWeeklyDashboard();
            if (state.currentTab === 'monthly') loadMonthlyDashboard();
        }
    } catch (err) {
        showToast(err.message, 'danger');
    }
}

function initModal() {
    const btnAddSubtask = document.getElementById('btn-add-subtask');
    if (btnAddSubtask && !btnAddSubtask.dataset.listenerAttached) {
        btnAddSubtask.dataset.listenerAttached = 'true';
        btnAddSubtask.addEventListener('click', () => {
            createSubtaskRow('', false);
        });
    }
}

function getLocalDateString(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// ==================== TASK MODAL (ADD / EDIT) ====================
function openAddTaskModal() {
    const backdrop = document.getElementById('task-modal-backdrop');
    const form = document.getElementById('task-form');
    const titleEl = document.getElementById('task-modal-title');
    const submitText = document.getElementById('task-form-submit-text');

    if (!backdrop || !form) return;

    form.reset();
    document.getElementById('task-form-id').value = '';
    titleEl.innerHTML = '<span class="modal-title-badge"><i class="fa-solid fa-plus"></i></span> Create New Mission';
    submitText.textContent = 'Save Task';

    const tagsInput = document.getElementById('task-form-tags');
    if (tagsInput) tagsInput.value = '';

    const subtaskList = document.getElementById('subtask-list');
    if (subtaskList) subtaskList.innerHTML = '';

    const dateInput = document.getElementById('task-form-date');
    if (dateInput) dateInput.value = getLocalDateString();

    backdrop.classList.remove('hidden');
    document.getElementById('task-form-title').focus();
}

function openEditTaskModal(taskId) {
    const task = state.tasks.find(t => t.id === taskId) || state.missedTasks.find(t => t.id === taskId);
    if (!task) return;

    const backdrop = document.getElementById('task-modal-backdrop');
    const titleEl = document.getElementById('task-modal-title');
    const submitText = document.getElementById('task-form-submit-text');

    document.getElementById('task-form-id').value = task.id;
    document.getElementById('task-form-title').value = task.title;
    document.getElementById('task-form-notes').value = task.notes || '';

    const tagsInput = document.getElementById('task-form-tags');
    if (tagsInput) tagsInput.value = task.tags || '';

    const subtaskList = document.getElementById('subtask-list');
    if (subtaskList) {
        subtaskList.innerHTML = '';
        if (Array.isArray(task.subtasks) && task.subtasks.length > 0) {
            task.subtasks.forEach(st => createSubtaskRow(st.title, st.is_done));
        }
    }

    const priority = task.priority || 'medium';
    const radio = document.querySelector(`input[name="task_priority"][value="${priority}"]`);
    if (radio) radio.checked = true;

    document.getElementById('task-form-date').value = task.original_date || '';
    if (task.deadline) {
        const d = new Date(task.deadline);
        const pad = n => String(n).padStart(2, '0');
        const dtStr = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        document.getElementById('task-form-deadline').value = dtStr;
    } else {
        document.getElementById('task-form-deadline').value = '';
    }

    titleEl.innerHTML = '<span class="modal-title-badge"><i class="fa-solid fa-pen-to-square"></i></span> Edit Mission Details';
    submitText.textContent = 'Update Task';

    backdrop.classList.remove('hidden');
    document.getElementById('task-form-title').focus();
}

function closeTaskModal() {
    const backdrop = document.getElementById('task-modal-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
    const btnSubmit = document.getElementById('btn-submit-task-form');
    if (btnSubmit) btnSubmit.disabled = false;
}

async function handleTaskFormSubmit(e) {
    e.preventDefault();
    const titleInput = document.getElementById('task-form-title');
    const title = titleInput.value.trim();

    if (!title) {
        titleInput.classList.add('shake-error');
        setTimeout(() => titleInput.classList.remove('shake-error'), 500);
        return;
    }

    const taskId = document.getElementById('task-form-id').value;
    const notes = document.getElementById('task-form-notes').value.trim();
    const priority = document.querySelector('input[name="task_priority"]:checked').value;
    const originalDate = document.getElementById('task-form-date').value;
    const deadlineVal = document.getElementById('task-form-deadline').value;
    const deadline = deadlineVal ? deadlineVal.replace('T', ' ') + ':00' : null;
    const tags = document.getElementById('task-form-tags') ? document.getElementById('task-form-tags').value.trim() : '';

    const subtaskRows = document.querySelectorAll('#subtask-list .subtask-row');
    const subtasks = [];
    subtaskRows.forEach((row, idx) => {
        const titleEl = row.querySelector('.subtask-row-title');
        const checkEl = row.querySelector('.subtask-row-check');
        const stTitle = titleEl ? titleEl.value.trim() : '';
        const isDone = checkEl ? checkEl.checked : false;
        if (stTitle) {
            subtasks.push({ title: stTitle, is_done: isDone, order_index: idx });
        }
    });

    const payload = {
        title,
        notes,
        priority,
        original_date: originalDate,
        deadline,
        tags,
        subtasks
    };

    const btnSubmit = document.getElementById('btn-submit-task-form');
    const submitText = document.getElementById('task-form-submit-text');
    if (submitText) submitText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving Mission...';
    if (btnSubmit) btnSubmit.disabled = true;

    closeTaskModal();

    if (!taskId) {
        // Optimistic Add: Instantly append temp card to container
        const tempId = 'temp_' + Date.now();
        const tempTask = {
            id: tempId,
            title,
            notes,
            priority,
            original_date: originalDate || getLocalDateString(),
            deadline,
            tags,
            is_boss: isBoss,
            status: 'pending',
            subtasks
        };

        const container = document.getElementById('today-tasks-list');
        if (container) {
            const tempHTML = createTaskCardHTML(tempTask);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = tempHTML;
            const tempCard = tempDiv.firstElementChild;
            if (tempCard) {
                tempCard.classList.add('task-card-pending-optimistic', 'task-card-slide-in');
                container.prepend(tempCard);
            }
        }

        showGlobalLoading('Deploying mission...');

        apiQueue.enqueue(async () => {
            try {
                const res = await api('/tasks', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                hideGlobalLoading();
                if (res.success) {
                    audio.play('click');
                    showToast('Task created and logged!', 'success');
                    await loadTodayTasks();
                    await loadUserProfile();
                    updateTabBadges();
                }
            } catch (err) {
                hideGlobalLoading();
                const tempCard = document.querySelector(`[data-task-id="${tempId}"]`);
                if (tempCard) tempCard.remove();
                showToast(`Failed to create task: ${err.message}`, 'danger');
            }
        });
    } else {
        // Edit Task
        showGlobalLoading('Updating mission...');
        apiQueue.enqueue(async () => {
            try {
                const res = await api(`/tasks/${taskId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                hideGlobalLoading();
                if (res.success) {
                    audio.play('click');
                    showToast('Task updated successfully!', 'success');
                    await loadTodayTasks();
                }
            } catch (err) {
                hideGlobalLoading();
                showToast(err.message, 'danger');
            }
        });
    }
}

// ==================== TASK LIFECYCLE LOGS MODAL ====================
async function openTaskLogsModal(taskId) {
    const task = state.tasks.find(t => t.id === taskId) || state.missedTasks.find(t => t.id === taskId);
    const backdrop = document.getElementById('logs-modal-backdrop');
    const heading = document.getElementById('logs-task-title');
    const timelineList = document.getElementById('logs-timeline-list');

    if (!backdrop || !timelineList) return;

    if (heading) heading.textContent = task ? task.title : `Task #${taskId}`;
    timelineList.innerHTML = '<div class="text-muted">Loading history...</div>';
    backdrop.classList.remove('hidden');

    try {
        const res = await api(`/tasks/${taskId}/logs`);
        if (res.success && res.logs) {
            if (res.logs.length === 0) {
                timelineList.innerHTML = '<div class="text-muted">No historical changes logged.</div>';
                return;
            }

            timelineList.innerHTML = res.logs.map(log => {
                const timeStr = log.changed_at_str ? new Date(log.changed_at_str).toLocaleString() : 'Recent';
                return `
                    <div class="timeline-item">
                        <div class="timeline-dot"></div>
                        <div class="timeline-content">
                            <div class="timeline-text">${escapeHTML(log.change_description)}</div>
                            <div class="timeline-time">${timeStr}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        timelineList.innerHTML = '<div class="text-danger">Failed to load logs.</div>';
    }
}

function closeLogsModal() {
    const backdrop = document.getElementById('logs-modal-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
}

// ==================== SECTION 3: WEEKLY DASHBOARD ====================
async function loadWeeklyDashboard(dateStr = state.activeWeeklyDate) {
    try {
        const data = await api(`/records/weekly?date=${dateStr}`);
        if (data.success && data.records) {
            renderWeeklyDashboard(data.records);
        }
    } catch (e) {
        console.error('Failed to load weekly records:', e);
    }
}

function renderWeeklyDashboard(rec) {
    state.activeWeeklyDate = rec.start_date;

    const rangeDisplay = document.getElementById('weekly-range-display');
    if (rangeDisplay) {
        rangeDisplay.textContent = `Week of ${rec.start_date} to ${rec.end_date}`;
    }

    const bestBanner = document.getElementById('weekly-best-day-text');
    const totalXpBanner = document.getElementById('weekly-total-xp');
    if (bestBanner && rec.best_day) {
        bestBanner.textContent = `Peak Momentum: ${rec.best_day.tasks_completed} tasks conquered on ${rec.best_day.full_day_name} (${rec.best_day.date})`;
    }
    if (totalXpBanner) {
        totalXpBanner.textContent = `+${rec.total_xp} XP Total Week`;
    }

    const grid = document.getElementById('weekly-grid-container');
    if (!grid) return;

    const maxComp = Math.max(1, ...rec.days.map(d => d.tasks_completed));

    grid.innerHTML = rec.days.map(d => {
        const heightPercent = Math.min(100, Math.round((d.tasks_completed / maxComp) * 100));
        const isBest = rec.best_day && rec.best_day.date === d.date && d.tasks_completed > 0;

        return `
            <div class="day-column-card ${d.is_today ? 'is-today' : ''} ${isBest ? 'is-best' : ''}">
                <div class="day-col-header">
                    <span class="day-col-name">${d.day_name}</span>
                    <span class="day-col-date">${d.date.slice(8, 10)}</span>
                </div>

                <div class="day-bar-wrapper" title="${d.tasks_completed} completed, ${d.tasks_missed} missed">
                    <div class="day-bar-fill" style="height: ${d.tasks_completed === 0 ? '4px' : heightPercent + '%'};"></div>
                </div>

                <div class="day-stat-label">
                    <span>${d.tasks_completed} Done</span>
                </div>
                <div class="day-xp-badge">
                    +${d.xp_earned} XP
                </div>
            </div>
        `;
    }).join('');

    const btnPrev = document.getElementById('btn-prev-week');
    const btnNext = document.getElementById('btn-next-week');
    const btnCurrent = document.getElementById('btn-current-week');

    if (btnPrev) btnPrev.onclick = () => loadWeeklyDashboard(rec.prev_week);
    if (btnNext) btnNext.onclick = () => loadWeeklyDashboard(rec.next_week);
    if (btnCurrent) btnCurrent.onclick = () => loadWeeklyDashboard('today');
}

// ==================== SECTION 3: MONTHLY HEATMAP DASHBOARD ====================
async function loadMonthlyDashboard(monthStr = state.activeMonthlyDate) {
    try {
        const query = monthStr ? `?month=${monthStr}` : '';
        const data = await api(`/records/monthly${query}`);
        if (data.success && data.records) {
            renderMonthlyDashboard(data.records);
        }
    } catch (e) {
        console.error('Failed to load monthly heatmap:', e);
    }
}

function renderMonthlyDashboard(rec) {
    state.activeMonthlyDate = rec.month;

    const titleDisplay = document.getElementById('monthly-title-display');
    if (titleDisplay) {
        titleDisplay.textContent = `${rec.month_name} ${rec.year} Activity`;
    }

    const totalComp = document.getElementById('monthly-stat-completed');
    const avgDaily = document.getElementById('monthly-stat-avg');
    const streakEl = document.getElementById('monthly-stat-streak');
    const peakEl = document.getElementById('monthly-stat-peak');

    if (totalComp) totalComp.textContent = rec.summary.total_completed;
    if (avgDaily) avgDaily.textContent = rec.summary.avg_daily;
    if (streakEl) streakEl.textContent = `${state.user ? state.user.streak : 0} Days`;
    if (peakEl) {
        peakEl.textContent = rec.summary.most_productive_count > 0 
            ? `${rec.summary.most_productive_count} tasks (${rec.summary.most_productive_date.slice(5)})` 
            : '--';
    }

    const matrix = document.getElementById('monthly-heatmap-matrix');
    if (!matrix) return;

    matrix.innerHTML = rec.days.map(d => {
        return `
            <div class="month-day-cell intensity-${d.intensity} ${d.is_today ? 'is-today' : ''}" 
                 data-date="${d.date}" 
                 title="${d.date}: ${d.completed} completed, ${d.pending} pending, ${d.missed} missed">
                <span class="day-num">${d.day}</span>
                <span class="day-task-count">${d.completed > 0 ? d.completed + '✓' : ''}</span>
            </div>
        `;
    }).join('');

    matrix.querySelectorAll('.month-day-cell').forEach(cell => {
        cell.addEventListener('click', () => {
            const date = cell.dataset.date;
            openDateDrilldownModal(date);
        });
    });

    const btnPrev = document.getElementById('btn-prev-month');
    const btnNext = document.getElementById('btn-next-month');
    const btnCurrent = document.getElementById('btn-current-month');

    if (btnPrev) btnPrev.onclick = () => loadMonthlyDashboard(rec.prev_month);
    if (btnNext) btnNext.onclick = () => loadMonthlyDashboard(rec.next_month);
    if (btnCurrent) btnCurrent.onclick = () => loadMonthlyDashboard(null);
}

// ==================== DATE DRILLDOWN MODAL ====================
async function openDateDrilldownModal(dateStr) {
    const backdrop = document.getElementById('date-tasks-modal-backdrop');
    const titleEl = document.getElementById('date-tasks-modal-title');
    const listEl = document.getElementById('date-tasks-modal-list');

    if (!backdrop || !listEl) return;

    titleEl.innerHTML = `<i class="fa-solid fa-calendar-day"></i> Missions for ${dateStr}`;
    listEl.innerHTML = '<div class="text-muted">Loading missions...</div>';
    backdrop.classList.remove('hidden');

    try {
        const data = await api(`/tasks/${dateStr}`);
        if (data.success && data.tasks) {
            if (data.tasks.length === 0) {
                listEl.innerHTML = '<div class="empty-state-card"><p>No tasks recorded on this date.</p></div>';
                return;
            }

            listEl.innerHTML = data.tasks.map(t => createTaskCardHTML(t)).join('');
        }
    } catch (e) {
        listEl.innerHTML = '<div class="text-danger">Failed to load tasks for date.</div>';
    }
}

function closeDateModal() {
    const backdrop = document.getElementById('date-tasks-modal-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
}

// ==================== SECTION 3: YEARLY MATRIX & CHART ====================
async function loadYearlyDashboard(yearStr = state.activeYearlyDate) {
    try {
        const query = yearStr ? `?year=${yearStr}` : '';
        const data = await api(`/records/yearly${query}`);
        if (data.success && data.records) {
            renderYearlyDashboard(data.records);
        }
    } catch (e) {
        console.error('Failed to load yearly records:', e);
    }
}

function renderYearlyDashboard(rec) {
    state.activeYearlyDate = rec.year;

    const titleDisplay = document.getElementById('yearly-title-display');
    if (titleDisplay) {
        titleDisplay.textContent = `Year ${rec.year} Productivity Velocity`;
    }

    const statTotal = document.getElementById('yearly-stat-total');
    const statFocus = document.getElementById('yearly-stat-focus');
    const statXp = document.getElementById('yearly-stat-xp');
    const statBadges = document.getElementById('yearly-stat-badges');

    if (statTotal) statTotal.textContent = rec.stats.total_completed;
    if (statFocus) statFocus.textContent = `${Math.round(rec.stats.total_focus_time_minutes / 60)} hrs`;
    if (statXp) statXp.textContent = `${rec.stats.total_xp} XP`;
    if (statBadges) statBadges.textContent = rec.stats.badges_unlocked;

    const grid = document.getElementById('yearly-heatmap-grid');
    if (grid) {
        grid.innerHTML = rec.heatmap.map(d => {
            return `
                <div class="year-day-pixel intensity-${d.intensity}" 
                     data-date="${d.date}" 
                     title="${d.date}: ${d.completed} completed"></div>
            `;
        }).join('');

        grid.querySelectorAll('.year-day-pixel').forEach(pixel => {
            pixel.addEventListener('click', () => {
                openDateDrilldownModal(pixel.dataset.date);
            });
        });
    }

    renderYearlyTrajectoryChart(rec.trend);

    const btnPrev = document.getElementById('btn-prev-year');
    const btnNext = document.getElementById('btn-next-year');
    const btnCurrent = document.getElementById('btn-current-year');

    if (btnPrev) btnPrev.onclick = () => loadYearlyDashboard(rec.prev_year);
    if (btnNext) btnNext.onclick = () => loadYearlyDashboard(rec.next_year);
    if (btnCurrent) btnCurrent.onclick = () => loadYearlyDashboard(null);
}

function renderYearlyTrajectoryChart(trend) {
    const canvas = document.getElementById('yearlyTrajectoryChart');
    if (!canvas || typeof Chart === 'undefined') return;

    if (state.yearlyChart) {
        state.yearlyChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.45)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

    state.yearlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.labels,
            datasets: [{
                label: 'Tasks Completed',
                data: trend.data,
                borderColor: '#6366f1',
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#fbbf24',
                pointBorderColor: '#6366f1',
                pointRadius: 4,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(16, 22, 34, 0.95)',
                    titleFont: { family: 'Sora', size: 12 },
                    bodyFont: { family: 'Inter', size: 12 },
                    padding: 10,
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { precision: 0, color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                }
            }
        }
    });
}

// ==================== SECTION 4: SHAME BOARD ====================
async function loadShameBoard() {
    try {
        const data = await api('/tasks/missed');
        if (data.success && data.tasks) {
            state.missedTasks = data.tasks;
            renderShameBoard();
        }
    } catch (e) {
        console.error('Failed to load shame board:', e);
    }
}

function renderShameBoard() {
    const list = document.getElementById('shame-task-list');
    const emptyState = document.getElementById('shame-empty-state');
    const shameBadge = document.getElementById('badge-missed-count');

    if (!list) return;

    if (shameBadge) {
        shameBadge.textContent = state.missedTasks.length;
        if (state.missedTasks.length > 0) {
            shameBadge.classList.remove('hidden');
        } else {
            shameBadge.classList.add('hidden');
        }
    }

    if (state.missedTasks.length === 0) {
        list.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    list.innerHTML = state.missedTasks.map(t => {
        return `
            <div class="shame-card" data-task-id="${t.id}">
                <div class="shame-alert-badge">
                    <i class="fa-solid fa-triangle-exclamation"></i> Overdue & Penalized
                </div>

                <div class="task-title text-danger">${escapeHTML(t.title)}</div>
                ${t.notes ? `<div class="task-notes">${escapeHTML(t.notes)}</div>` : ''}

                <div class="shame-timestamp">
                    <i class="fa-regular fa-clock"></i> Ignored since ${t.deadline_str || t.original_date} (${t.days_overdue || 1} days overdue)
                </div>

                <div class="task-card-footer">
                    <div class="priority-tag priority-${t.priority || 'medium'}">${t.priority} Priority</div>
                    <div class="task-actions">
                        <button class="btn btn-sm btn-primary" data-action="toggle-complete">
                            <i class="fa-solid fa-check"></i> Redeem Now
                        </button>
                        <button class="btn-action delete-btn" data-action="delete-task" title="Delete Task">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== SECTION 4: ACHIEVEMENTS & BADGES ====================
async function loadBadgesShowcase() {
    try {
        const data = await api('/user/badges');
        if (data.success && data.badges) {
            renderBadgesShowcase(data.badges);
        }
    } catch (e) {
        console.error('Failed to load badges:', e);
    }
}

function renderBadgesShowcase(badges) {
    const container = document.getElementById('badges-container');
    if (!container) return;

    container.innerHTML = badges.map(b => {
        return `
            <div class="badge-card ${b.unlocked ? 'unlocked' : 'locked'}">
                <div class="badge-icon-box tier-${b.tier || 'bronze'}">
                    <i class="fa-solid ${b.icon || 'fa-medal'}"></i>
                </div>
                <div class="badge-info">
                    <h4>${b.title}</h4>
                    <p>${b.description}</p>
                    <span class="badge-status-tag">
                        ${b.unlocked ? `✓ Unlocked (${b.earned_at ? b.earned_at.slice(0, 10) : 'Earned'})` : '🔒 Locked'}
                    </span>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== DELETE MISSION MODAL & OPTIMISTIC DELETE ====================
function openDeleteConfirmModal(taskId) {
    state.taskToDeleteId = taskId;
    const backdrop = document.getElementById('delete-modal-backdrop');
    if (backdrop) backdrop.classList.remove('hidden');
}

function closeDeleteConfirmModal() {
    state.taskToDeleteId = null;
    const backdrop = document.getElementById('delete-modal-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
}

async function confirmDeleteTask() {
    const taskId = state.taskToDeleteId;
    if (!taskId) return;

    closeDeleteConfirmModal();

    // 1. Optimistic UI: Find task card and trigger 300ms collapse + slide-out fade
    const card = document.querySelector(`[data-task-id="${taskId}"]`);
    const backupTask = (state.tasks || []).find(t => t.id === taskId);
    const backupIndex = (state.tasks || []).findIndex(t => t.id === taskId);

    if (card) {
        card.classList.add('is-deleting');
    }

    // Remove from local state immediately
    if (backupIndex !== -1) {
        state.tasks.splice(backupIndex, 1);
    }

    // Remove DOM element after 300ms transition
    setTimeout(() => {
        if (card && card.parentNode) card.remove();
        updateTabBadges();
    }, 300);

    // 2. Queue background API call
    apiQueue.enqueue(async () => {
        try {
            await api(`/tasks/${taskId}`, { method: 'DELETE' });
            audio.play('click');
            showToast('Mission obliterated!', 'info');
        } catch (err) {
            showToast(`Failed to delete task: ${err.message}`, 'danger');
            // Rollback optimistic delete: restore to state and re-render with red shake
            if (backupTask && backupIndex !== -1) {
                state.tasks.splice(backupIndex, 0, backupTask);
            }
            await loadTodayTasks();
            const restoredCard = document.querySelector(`[data-task-id="${taskId}"]`);
            if (restoredCard) {
                restoredCard.classList.add('shake-card-error');
                setTimeout(() => restoredCard.classList.remove('shake-card-error'), 500);
            }
        }
    });
}

// ==================== MYSTERY REWARD CHEST ====================
async function openRewardChestModal() {
    const backdrop = document.getElementById('chest-modal-backdrop');
    if (!backdrop) return;

    backdrop.classList.remove('hidden');
    audio.play('chest');
    launchConfetti('golden');
    triggerParticleBurst(window.innerWidth / 2, window.innerHeight / 2);
    animateMilestoneWipe();

    try {
        const res = await api('/rewards/chest', { method: 'POST' });
        if (res.success && res.reward) {
            const r = res.reward;
            document.getElementById('chest-reward-title').textContent = r.title;
            document.getElementById('chest-reward-desc').textContent = r.desc;
            
            const iconEl = document.getElementById('chest-reward-icon');
            if (iconEl) {
                iconEl.className = `fa-solid ${r.icon || 'fa-crown'}`;
            }

            if (res.profile) {
                state.user = res.profile;
                renderGamificationHeader();
            }
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

function closeRewardChestModal() {
    const backdrop = document.getElementById('chest-modal-backdrop');
    if (backdrop) backdrop.classList.add('hidden');
}

// ==================== UTILITY FUNCTIONS ====================
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function updateLiveDateDisplay() {
    const dateDisplay = document.getElementById('current-date-display');
    if (dateDisplay) {
        const now = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.textContent = now.toLocaleDateString(undefined, options);
    }
}

// ==================== SECTION 5: DAILY & WEEKLY CHALLENGES ====================
async function loadChallenges() {
    try {
        const res = await api('/challenges');
        if (res.success && res.challenges) {
            state.challenges = res.challenges;
            renderChallenges();
        }
    } catch (e) {
        console.error('Failed to load challenges:', e);
    }
}

function renderChallenges() {
    const badgeCount = document.getElementById('badge-challenges-count');
    if (badgeCount) {
        badgeCount.classList.add('hidden');
        badgeCount.textContent = '';
    }

    const renderCard = (c) => `
        <div class="challenge-card glass-card">
            <div class="challenge-header">
                <div class="challenge-title-group">
                    <h4>${escapeHTML(c.title)}</h4>
                    <p>${escapeHTML(c.description)}</p>
                </div>
                <div class="challenge-reward-badge">+${c.xp_reward} XP</div>
            </div>
            <div class="challenge-progress-bar">
                <div class="challenge-progress-fill" style="width: ${c.progress_percent || 0}%;"></div>
            </div>
            <div class="challenge-footer">
                <span class="challenge-stat-text">${c.current_count} / ${c.target_count} Completed</span>
                ${c.is_claimed ? `
                    <span class="badge-status-tag">✓ Claimed</span>
                ` : c.is_completed ? `
                    <button class="btn btn-sm btn-primary glow-button" onclick="claimChallenge(${c.id})">
                        <i class="fa-solid fa-gift"></i> Claim Reward
                    </button>
                ` : `
                    <span class="text-muted" style="font-size: 11.5px;"><i class="fa-solid fa-spinner fa-spin"></i> In Progress</span>
                `}
            </div>
        </div>
    `;

    if (dailyContainer) dailyContainer.innerHTML = daily.map(renderCard).join('') || '<div class="text-muted">No active daily quests.</div>';
    if (weeklyContainer) weeklyContainer.innerHTML = weekly.map(renderCard).join('') || '<div class="text-muted">No active weekly quests.</div>';

    // Milestone Rewards Unlocks Track
    const userXp = (state.user && state.user.xp) || 0;
    const m500 = document.getElementById('milestone-500-status');
    const m1000 = document.getElementById('milestone-1000-status');
    const m2500 = document.getElementById('milestone-2500-status');
    if (m500) m500.innerHTML = userXp >= 500 ? '<span class="text-emerald font-bold">✓ Unlocked (Neon Cyber)</span>' : '🔒 Requires 500 XP';
    if (m1000) m1000.innerHTML = userXp >= 1000 ? '<span class="text-emerald font-bold">✓ Unlocked (Boss Mode)</span>' : '🔒 Requires 1,000 XP';
    if (m2500) m2500.innerHTML = userXp >= 2500 ? '<span class="text-emerald font-bold">✓ Unlocked (Apex Overlord)</span>' : '🔒 Requires 2,500 XP';
}

async function claimChallenge(challengeId) {
    try {
        const res = await api(`/challenges/${challengeId}/claim`, { method: 'POST' });
        if (res.success) {
            audio.play('chest');
            launchConfetti('default');
            showToast(`🎉 Quest Claimed! +${res.xp_reward} XP added!`, 'success');
            if (res.profile) {
                state.user = res.profile;
                renderGamificationHeader();
            }
            await loadChallenges();
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// ==================== SECTION 6: FOCUS MODE ====================
function toggleFocusMode(forceState = null) {
    const isActive = forceState !== null ? forceState : !document.body.classList.contains('focus-mode-active');
    const exitPill = document.getElementById('focus-mode-exit-pill');

    if (isActive) {
        document.body.classList.add('focus-mode-active');
        if (exitPill) exitPill.classList.remove('hidden');
        showToast('🎯 Focus Mode: Distractions silenced (Press Esc or F to exit)', 'info', 'fa-crosshairs');
    } else {
        document.body.classList.remove('focus-mode-active');
        if (exitPill) exitPill.classList.add('hidden');
        showToast('Focus Mode exited', 'info');
    }
}

// ==================== SECTION 7: CUSTOM ACCENT COLOR PICKER ====================
function hexToRgba(hex, alpha = 1) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function applyAccentColor(color) {
    if (!color) return;
    document.documentElement.style.setProperty('--primary', color);
    document.documentElement.style.setProperty('--primary-glow', hexToRgba(color, 0.45));
    document.documentElement.style.setProperty('--accent', color);

    const preview = document.getElementById('accent-color-preview');
    if (preview) preview.style.background = color;
    const input = document.getElementById('custom-accent-input');
    if (input) input.value = color;

    localStorage.setItem('apextask_custom_accent', color);
}

function initAccentColor() {
    const saved = localStorage.getItem('apextask_custom_accent') || '#8b5cf6';
    applyAccentColor(saved);

    const input = document.getElementById('custom-accent-input');
    if (input) {
        input.addEventListener('input', (e) => applyAccentColor(e.target.value));
        input.addEventListener('change', (e) => applyAccentColor(e.target.value));
    }
}

// ==================== SECTION 8: KEYBOARD CONTROLLER ====================
const keyboardController = {
    init() {
        document.addEventListener('keydown', (e) => {
            const activeEl = document.activeElement;
            const isTyping = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable);

            // Esc closes modals and exits Focus Mode
            if (e.key === 'Escape') {
                const openModals = document.querySelectorAll('.modal-backdrop:not(.hidden)');
                if (openModals.length > 0) {
                    openModals.forEach(m => m.classList.add('hidden'));
                    return;
                }
                if (document.body.classList.contains('focus-mode-active')) {
                    toggleFocusMode(false);
                    return;
                }
            }

            // If typing in input, don't trigger single-letter hotkeys
            if (isTyping) return;

            if (e.key === 'n' || e.key === 'N') {
                e.preventDefault();
                openAddTaskModal();
            } else if (e.key === 'd' || e.key === 'D') {
                e.preventDefault();
                const firstPending = state.tasks.find(t => t.status === 'pending');
                if (firstPending) {
                    handleToggleComplete(firstPending.id);
                } else {
                    showToast('No pending tasks to mark complete!', 'info');
                }
            } else if (e.key === 'f' || e.key === 'F') {
                e.preventDefault();
                toggleFocusMode();
            } else if (e.key === '/') {
                e.preventDefault();
                const searchInput = document.getElementById('task-search-input');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            } else if (e.key === '?' || (e.shiftKey && e.key === '/')) {
                e.preventDefault();
                openShortcutsModal();
            }
        });
    }
};

function openShortcutsModal() {
    const modal = document.getElementById('shortcuts-modal-backdrop');
    if (modal) modal.classList.remove('hidden');
}

function closeShortcutsModal() {
    const modal = document.getElementById('shortcuts-modal-backdrop');
    if (modal) modal.classList.add('hidden');
}

function openImportExportModal() {
    const modal = document.getElementById('import-export-modal-backdrop');
    if (modal) modal.classList.remove('hidden');
}

function closeImportExportModal() {
    const modal = document.getElementById('import-export-modal-backdrop');
    if (modal) modal.classList.add('hidden');
}

// ==================== SECTION 9: TASK IMPORT & EXPORT ====================
async function handleExportTasks(format = 'json') {
    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/tasks/export?format=${format}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Export failed');

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `apextask_export_${new Date().toISOString().slice(0, 10)}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showToast(`Missions exported successfully as ${format.toUpperCase()}!`, 'success');
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

async function handleImportTasks(file) {
    if (!file) return;
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);

    try {
        showToast('Importing tasks...', 'info');
        const res = await fetch(`${API_BASE}/tasks/import`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            audio.play('complete');
            showToast(data.message || `Imported ${data.imported_count} tasks!`, 'success');
            closeImportExportModal();
            await loadTodayTasks();
        } else {
            showToast(data.error || 'Failed to import tasks', 'danger');
        }
    } catch (e) {
        showToast(e.message, 'danger');
    }
}

// ==================== INITIALIZATION & EVENT LISTENERS ====================
document.addEventListener('DOMContentLoaded', async () => {
    // 0. Enforce Authentication Guard on app.html
    const isAuthenticated = await verifyAuthentication();
    if (!isAuthenticated) return;

    // 1. Initialize Theme from localStorage
    const savedTheme = localStorage.getItem('apextask_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.querySelectorAll('.theme-pill').forEach(pill => {
        if (pill.dataset.themeVal === savedTheme) pill.classList.add('active');
        else pill.classList.remove('active');
    });

    // Theme switch listener
    document.querySelectorAll('.theme-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const val = pill.dataset.themeVal;
            document.documentElement.setAttribute('data-theme', val);
            localStorage.setItem('apextask_theme', val);
            document.querySelectorAll('.theme-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            audio.play('click');
        });
    });

    // 2. Sound Toggle
    const soundToggle = document.getElementById('sound-toggle');
    const soundIcon = document.getElementById('sound-icon');
    const savedSound = localStorage.getItem('apextask_sound');
    if (savedSound !== null) {
        state.soundEnabled = savedSound === 'true';
    }
    if (soundToggle && soundIcon) {
        if (!state.soundEnabled) {
            soundToggle.classList.add('muted');
            soundIcon.className = 'fa-solid fa-volume-xmark';
        }
        soundToggle.addEventListener('click', () => {
            state.soundEnabled = !state.soundEnabled;
            localStorage.setItem('apextask_sound', state.soundEnabled);
            if (state.soundEnabled) {
                soundToggle.classList.remove('muted');
                soundIcon.className = 'fa-solid fa-volume-high';
                audio.play('click');
            } else {
                soundToggle.classList.add('muted');
                soundIcon.className = 'fa-solid fa-volume-xmark';
            }
        });
    }

    // Mobile Navigation Sidebar Drawer Controller
    const btnMobileMenuToggle = document.getElementById('btn-mobile-menu-toggle');
    const appSidebar = document.getElementById('app-sidebar');
    const mobileBackdrop = document.getElementById('mobile-sidebar-backdrop');

    function openMobileSidebar() {
        if (appSidebar) appSidebar.classList.add('mobile-open');
        if (mobileBackdrop) mobileBackdrop.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        if (appSidebar) appSidebar.classList.remove('mobile-open');
        if (mobileBackdrop) mobileBackdrop.classList.add('hidden');
        document.body.style.overflow = '';
    }

    if (btnMobileMenuToggle) {
        btnMobileMenuToggle.addEventListener('click', () => {
            if (appSidebar && appSidebar.classList.contains('mobile-open')) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        });
    }

    if (mobileBackdrop) {
        mobileBackdrop.addEventListener('click', closeMobileSidebar);
    }

    // 3. Navigation Tabs Switching
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            if (state.currentTab === tabId) return;

            state.currentTab = tabId;
            audio.play('click');
            closeMobileSidebar();
            startTopLoadingBar();

            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.view-section').forEach(sec => {
                sec.classList.add('hidden');
                sec.classList.remove('view-section-fade-in');
            });
            const targetSection = document.getElementById(`view-${tabId}`);
            if (targetSection) {
                targetSection.classList.remove('hidden');
                void targetSection.offsetWidth; // Trigger reflow for animation
                targetSection.classList.add('view-section-fade-in');
            }

            if (tabId === 'today') {
                renderSkeletonCards('today-task-list', 3);
                loadTodayTasks();
            } else if (tabId === 'challenges') loadChallenges();
            else if (tabId === 'weekly') loadWeeklyDashboard();
            else if (tabId === 'monthly') loadMonthlyDashboard();
            else if (tabId === 'yearly') loadYearlyDashboard();
            else if (tabId === 'shame') loadShameBoard();
            else if (tabId === 'badges') loadBadgesShowcase();
        });
    });

    // 4. Filter Pills in Today's View
    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const filterVal = pill.dataset.filter;
            if (state.currentFilter === filterVal) return;

            state.currentFilter = filterVal;
            audio.play('click');
            startTopLoadingBar();

            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            // Quick skeleton pulse transition for filter shift
            renderSkeletonCards('today-task-list', 2);
            setTimeout(() => {
                renderTodayTasks();
                finishTopLoadingBar();
            }, 120);
        });
    });

    // 5. Search Bar in Today's View (Fuzzy Levenshtein Real-time)
    const searchInput = document.getElementById('task-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            renderTodayTasks();
        });
    }

    // 6. Add Task Button & Empty state add button
    const btnOpenAdd = document.getElementById('btn-open-add-task');
    const btnEmptyAdd = document.getElementById('btn-empty-add-task');
    if (btnOpenAdd) btnOpenAdd.addEventListener('click', openAddTaskModal);
    if (btnEmptyAdd) btnEmptyAdd.addEventListener('click', openAddTaskModal);

    // 7. Modals close buttons
    const btnCloseTaskModal = document.getElementById('btn-close-task-modal');
    const btnCancelTaskForm = document.getElementById('btn-cancel-task-form');
    if (btnCloseTaskModal) btnCloseTaskModal.addEventListener('click', closeTaskModal);
    if (btnCancelTaskForm) btnCancelTaskForm.addEventListener('click', closeTaskModal);

    const btnCloseLogsModal = document.getElementById('btn-close-logs-modal');
    if (btnCloseLogsModal) btnCloseLogsModal.addEventListener('click', closeLogsModal);

    const btnCloseDateModal = document.getElementById('btn-close-date-modal');
    if (btnCloseDateModal) btnCloseDateModal.addEventListener('click', closeDateModal);

    const btnCloseChestModal = document.getElementById('btn-close-chest-modal');
    const btnClaimReward = document.getElementById('btn-claim-reward');
    if (btnCloseChestModal) btnCloseChestModal.addEventListener('click', closeRewardChestModal);
    if (btnClaimReward) btnClaimReward.addEventListener('click', closeRewardChestModal);

    // Shortcuts modal
    const btnOpenShortcuts = document.getElementById('btn-open-shortcuts');
    const btnCloseShortcuts = document.getElementById('btn-close-shortcuts-modal');
    if (btnOpenShortcuts) btnOpenShortcuts.addEventListener('click', openShortcutsModal);
    if (btnCloseShortcuts) btnCloseShortcuts.addEventListener('click', closeShortcutsModal);

    // Import / Export modal
    const btnOpenImportExport = document.getElementById('btn-open-import-export');
    const btnCloseImportExport = document.getElementById('btn-close-import-export-modal');
    if (btnOpenImportExport) btnOpenImportExport.addEventListener('click', openImportExportModal);
    if (btnCloseImportExport) btnCloseImportExport.addEventListener('click', closeImportExportModal);

    // Level up modal close
    const btnCloseLevelup = document.getElementById('btn-close-levelup-modal');
    const btnClaimLevelup = document.getElementById('btn-claim-levelup');
    if (btnCloseLevelup) btnCloseLevelup.addEventListener('click', () => document.getElementById('levelup-modal-backdrop').classList.add('hidden'));
    if (btnClaimLevelup) btnClaimLevelup.addEventListener('click', () => document.getElementById('levelup-modal-backdrop').classList.add('hidden'));

    // Focus mode button & exit pill
    const btnFocusMode = document.getElementById('btn-focus-mode');
    const exitFocusPill = document.getElementById('focus-mode-exit-pill');
    if (btnFocusMode) btnFocusMode.addEventListener('click', () => toggleFocusMode());
    if (exitFocusPill) exitFocusPill.addEventListener('click', () => toggleFocusMode(false));

    // Export JSON & CSV buttons
    const btnExportJson = document.getElementById('btn-export-json');
    const btnExportCsv = document.getElementById('btn-export-csv');
    if (btnExportJson) btnExportJson.addEventListener('click', () => handleExportTasks('json'));
    if (btnExportCsv) btnExportCsv.addEventListener('click', () => handleExportTasks('csv'));

    // Import file input & drag/drop
    const fileInput = document.getElementById('tasks-file-input');
    const dropZone = document.getElementById('import-drop-zone');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) handleImportTasks(e.target.files[0]);
        });
    }
    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput && fileInput.click());
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleImportTasks(e.dataTransfer.files[0]);
            }
        });
    }

    // Delete confirmation modal buttons
    const btnCancelDelete = document.getElementById('btn-cancel-delete');
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    if (btnCancelDelete) btnCancelDelete.addEventListener('click', closeDeleteConfirmModal);
    if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', confirmDeleteTask);

    // Chest widget trigger click
    const chestTrigger = document.getElementById('chest-trigger');
    if (chestTrigger) {
        chestTrigger.addEventListener('click', () => {
            openRewardChestModal();
        });
    }

    // Reset All Gamification Progress Button
    const btnResetGamification = document.getElementById('btn-reset-all-gamification');
    if (btnResetGamification) {
        btnResetGamification.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to reset all Levels, XP, Streaks, and Milestone Badges back to 0?')) return;
            try {
                const res = await api('/user/reset', { method: 'POST' });
                if (res.success && res.profile) {
                    state.user = res.profile;
                    renderGamificationHeader();
                    await loadBadgesShowcase();
                    showToast('All levels, XP, and milestones have been reset to 0!', 'info');
                }
            } catch (err) {
                showToast(err.message, 'danger');
            }
        });
    }

    // Manual Rollover Button
    const btnManualRollover = document.getElementById('btn-manual-rollover');
    if (btnManualRollover) {
        btnManualRollover.addEventListener('click', () => {
            triggerAutoRollover(true);
        });
    }

    // Logout Button in Header
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
        btnLogout.addEventListener('click', () => {
            if (confirm('Are you sure you want to log out?')) {
                handleLogout();
            }
        });
    }

    // Global Delegated Click Handler for all Task Action Buttons (Toggle, Edit, Delete, Logs)
    document.addEventListener('click', async (e) => {
        const actionBtn = e.target.closest('[data-action]');
        if (!actionBtn) return;

        const action = actionBtn.dataset.action;
        const card = actionBtn.closest('[data-task-id]');
        if (!card) return;

        const taskId = parseInt(card.dataset.taskId, 10);
        if (!taskId) return;

        e.preventDefault();
        e.stopPropagation();

        if (action === 'toggle-complete') {
            await handleToggleComplete(taskId);
        } else if (action === 'edit-task') {
            openEditTaskModal(taskId);
        } else if (action === 'delete-task') {
            openDeleteConfirmModal(taskId);
        } else if (action === 'view-logs') {
            openTaskLogsModal(taskId);
        }
    });

    // Modal backdrop click to close
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.classList.add('hidden');
            }
        });
    });

    // 8. Task Form Submit & Modal Initialization
    const taskForm = document.getElementById('task-form');
    if (taskForm) taskForm.addEventListener('submit', handleTaskFormSubmit);
    initModal();

    // Live Date Display Helper
    function updateLiveDateDisplay() {
        const el = document.getElementById('current-date-display');
        if (!el) return;
        const now = new Date();
        const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
        el.textContent = now.toLocaleDateString('en-US', options);
    }

    // 9. Initial App Load, Controllers & Auto Rollover
    updateLiveDateDisplay();
    initAccentColor();
    keyboardController.init();
    renderGamificationHeader();
    await triggerAutoRollover(false);
    await loadTodayTasks();
    await loadChallenges();
    await loadShameBoard();
});
