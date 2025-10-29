// Global state
let currentSnippetId = null;
let currentWeekStart = null;
let currentWeekEnd = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeDefaultView();
    setupDateInputs();
});

function setupDateInputs() {
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');

    // When start changes: ensure it's a Monday (snap to Monday), and that end >= start
    startInput.addEventListener('change', () => {
        if (!startInput.value) return;
        const selected = new Date(startInput.value);
        const monday = getWeekDates(selected).monday;
        startInput.value = monday; // snap to Monday

        if (endInput.value) {
            const endDate = new Date(endInput.value);
            if (endDate < new Date(startInput.value)) {
                alert('End date must be greater than or equal to start date. Adjusting end to the Sunday of the selected week.');
                endInput.value = getWeekDates(new Date(startInput.value)).sunday;
            }
        }

        loadSnippets();
    });

    // When end changes: ensure it's a Sunday (snap to Sunday), and that end >= start
    endInput.addEventListener('change', () => {
        if (!endInput.value) return;
        const selected = new Date(endInput.value);
        const sunday = getWeekDates(selected).sunday;
        endInput.value = sunday; // snap to Sunday

        if (startInput.value) {
            const startDate = new Date(startInput.value);
            if (new Date(endInput.value) < startDate) {
                alert('End date must be greater than or equal to start date. Adjusting start to the Monday of the selected week.');
                startInput.value = getWeekDates(new Date(endInput.value)).monday;
            }
        }

        loadSnippets();
    });
}

function getWeekDates(date) {
    // Normalize input to local date (avoid TZ issues with Date parsing of YYYY-MM-DD)
    let d;
    if (typeof date === 'string') {
        const parts = date.split('-').map(Number);
        // parts: [YYYY, MM, DD]
        d = new Date(parts[0], parts[1] - 1, parts[2]);
    } else if (date instanceof Date) {
        d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    } else {
        d = new Date();
        d.setHours(0,0,0,0);
    }

    const day = d.getDay(); // 0 (Sun) .. 6 (Sat)
    // Calculate Monday of this week
    const monday = new Date(d);
    const offsetToMonday = (day === 0) ? -6 : (1 - day);
    monday.setDate(d.getDate() + offsetToMonday);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return {
        monday: formatDate(monday),
        sunday: formatDate(sunday),
        mondayObj: monday,
        sundayObj: sunday
    };
}

function formatDate(date) {
    // Format YYYY-MM-DD using local date components to avoid timezone shifts
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function formatDateDisplay(dateStr) {
    // Parse YYYY-MM-DD into local date to avoid timezone issues
    const parts = String(dateStr).split('-').map(Number);
    const date = new Date(parts[0], parts[1] - 1, parts[2]);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

function getWeekNumber(date) {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

async function initializeDefaultView() {
    // Default date range per spec:
    // Start = Monday of (current week - 4 weeks)
    // End   = Sunday of current week
    const today = new Date();

    // Get current week's Monday and Sunday
    const currentWeek = getWeekDates(today);

    // Compute Monday of current week minus 4 weeks
    const startMondayObj = new Date(currentWeek.mondayObj);
    startMondayObj.setDate(startMondayObj.getDate() - (4 * 7));

    // start = Monday of (current week - 4 weeks)
    const startStr = formatDate(startMondayObj);
    // end = Sunday of current week
    const endStr = currentWeek.sunday;

    document.getElementById('startDate').value = startStr;
    document.getElementById('endDate').value = endStr;

    await loadSnippets();
}

async function goToCurrentWeek() {
    // Set date range to current week only:
    // Start = Monday of current week
    // End   = Sunday of current week
    const today = new Date();

    // Get current week's Monday and Sunday
    const currentWeek = getWeekDates(today);

    document.getElementById('startDate').value = currentWeek.monday;
    document.getElementById('endDate').value = currentWeek.sunday;

    await loadSnippets();
}

async function navigateWeek(direction) {
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');

    // Parse dates as local dates to avoid timezone issues
    const startParts = startInput.value.split('-').map(Number);
    const startDate = new Date(startParts[0], startParts[1] - 1, startParts[2]);

    const endParts = endInput.value.split('-').map(Number);
    const endDate = new Date(endParts[0], endParts[1] - 1, endParts[2]);

    // Move both dates forward/backward by a week
    startDate.setDate(startDate.getDate() + (direction * 7));
    endDate.setDate(endDate.getDate() + (direction * 7));

    // Update the inputs with the new dates
    startInput.value = formatDate(startDate);
    endInput.value = formatDate(endDate);

    await loadSnippets();
}

async function loadSnippets() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) return;

    // Parse dates properly as local dates to avoid timezone issues
    const startParts = startDate.split('-').map(Number);
    const start = new Date(startParts[0], startParts[1] - 1, startParts[2]);

    const endParts = endDate.split('-').map(Number);
    const end = new Date(endParts[0], endParts[1] - 1, endParts[2]);

    if (end < start) {
        alert('End date must be greater than or equal to start date');
        return;
    }

    // Compute the universe of weeks (includes week containing start, week containing end, and all weeks between)
    const universe = computeUniverseWeeks(startDate, endDate);

    // Query API using full-week boundaries so server returns snippets for those weeks
    const queryStart = universe[0].week_start;
    const queryEnd = universe[universe.length - 1].week_end;

    try {
        const response = await fetch(`/api/snippets?start_date=${queryStart}&end_date=${queryEnd}`);
        const snippets = await response.json();

        // Map snippets by week_start for easy lookup
        const snippetsMap = {};
        snippets.forEach(s => { snippetsMap[s.week_start] = s; });

        displayWeeks(universe, snippetsMap);
    } catch (error) {
        console.error('Error loading snippets:', error);
    }
}

// Compute the array of weeks (week_start, week_end, Date objects, isFuture)
function computeUniverseWeeks(startDateStr, endDateStr) {
    // Parse dates as local dates to avoid timezone issues
    const startParts = startDateStr.split('-').map(Number);
    const startDate = new Date(startParts[0], startParts[1] - 1, startParts[2]);

    const endParts = endDateStr.split('-').map(Number);
    const endDate = new Date(endParts[0], endParts[1] - 1, endParts[2]);

    // Get Monday for start and Monday for end
    const startWeek = getWeekDates(startDate);
    const endWeek = getWeekDates(endDate);

    const weeks = [];
    let cursor = new Date(startWeek.mondayObj);
    const endCursor = new Date(endWeek.mondayObj);

    const today = new Date();
    today.setHours(0,0,0,0);

    while (cursor <= endCursor) {
        const monday = new Date(cursor);
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);

        const weekStartStr = formatDate(monday);
        const weekEndStr = formatDate(sunday);

        const isFuture = monday > today; // week starts in the future

        weeks.push({
            week_start: weekStartStr,
            week_end: weekEndStr,
            weekStartObj: monday,
            weekEndObj: sunday,
            isFuture
        });

        // Move to next week
        cursor.setDate(cursor.getDate() + 7);
    }

    return weeks;
}

// Render the weeks universe and snippets map
function displayWeeks(weeks, snippetsMap) {
    const container = document.getElementById('snippetsContainer');

    if (!weeks || weeks.length === 0) {
        container.innerHTML = '<p>No weeks to display</p>';
        return;
    }

    let html = '';

    // Render weeks in reverse chronological order (latest week first)
    for (let i = weeks.length - 1; i >= 0; i--) {
        const week = weeks[i];
        const weekNum = getWeekNumber(week.week_start);
        const startFormatted = formatDateDisplay(week.week_start);
        const endFormatted = formatDateDisplay(week.week_end);

        html += `<div class="week-section">`;
        html += `  <div class="week-header">`;
        html += `    <span class="week-badge">Week ${weekNum}</span>`;
        html += `    <h2 class="week-title">${startFormatted} – ${endFormatted}</h2>`;

        // If snippet exists for this week, render it
        const snippet = snippetsMap[week.week_start];
        html += `  </div>`;
        html += `  <div class="snippet-content">`;
        if (snippet) {
            const enableMarkdown = true;
            const contentHtml = enableMarkdown ? marked.parse(snippet.content) : escapeHtml(snippet.content);
            html += contentHtml;
            html += `  </div>`;
            html += `  <button class="edit-btn" onclick="openEditModal(${snippet.id})">Edit</button>`;
        } else {
            // No snippet for this week — per spec show only the Add Snippets button (no "No snippets" text)
            html += `  </div>`;
            html += `  <button class="add-snippet-btn" onclick="openNewSnippetModalForWeek('${week.week_start}','${week.week_end}')">Add Snippets</button>`;
        }

        html += `</div>`;
    }

    container.innerHTML = html;
}

function displaySnippets(snippets) {
    const container = document.getElementById('snippetsContainer');
    
    if (snippets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM7 10h2v7H7zm4-3h2v10h-2zm4 6h2v4h-2z"/>
                </svg>
                <h3>No snippets for this date range</h3>
                <p>Create your first snippet for this week!</p>
                <button class="add-snippet-btn" onclick="openNewSnippetModal()">Add Snippet</button>
            </div>
        `;
        return;
    }
    
    let html = '<button class="add-snippet-btn" onclick="openNewSnippetModal()">Add Snippet</button>';
    
    // Ensure snippets are shown in reverse chronological order (latest week first)
    snippets.sort((a, b) => new Date(b.week_start) - new Date(a.week_start));

    snippets.forEach(snippet => {
        const weekNum = getWeekNumber(snippet.week_start);
        const startFormatted = formatDateDisplay(snippet.week_start);
        const endFormatted = formatDateDisplay(snippet.week_end);
        
        const enableMarkdown = true; // You can store this preference
        const contentHtml = enableMarkdown ? marked.parse(snippet.content) : escapeHtml(snippet.content);
        
        html += `
            <div class="week-section">
                <div class="week-header">
                    <span class="week-badge">Current week</span>
                    <h2 class="week-title">Week ${weekNum}</h2>
                    <span class="week-date">· ${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]}</span>
                    <button style="margin-left: auto; padding: 4px 8px; border: none; background: none; color: #1a73e8; cursor: pointer;" onclick="copyWeekLink('${snippet.week_start}')">🔗</button>
                </div>
                <div class="snippet-content">
                    ${contentHtml}
                </div>
                <button class="edit-btn" onclick="openEditModal(${snippet.id})">Edit</button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyWeekLink(weekStart) {
    const url = `${window.location.origin}/?week=${weekStart}`;
    navigator.clipboard.writeText(url);
    alert('Link copied to clipboard!');
}

function openNewSnippetModal() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select a date range first');
        return;
    }
    
    currentSnippetId = null;
    // Use the week containing the start date as the target week (snippets belong to a single week)
    const week = getWeekDates(new Date(startDate));
    currentWeekStart = week.monday;
    currentWeekEnd = week.sunday;
    
    const weekNum = getWeekNumber(startDate);
    const startFormatted = formatDateDisplay(currentWeekStart);
    const endFormatted = formatDateDisplay(currentWeekEnd);
    
    document.getElementById('modalTitle').textContent = `New Snippet - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
    document.getElementById('snippetContent').value = '';
    
    showModal();
}

// Open the new snippet modal for a specific week (week boundaries passed)
function openNewSnippetModalForWeek(weekStart, weekEnd) {
    currentSnippetId = null;
    currentWeekStart = weekStart;
    currentWeekEnd = weekEnd;

    const weekNum = getWeekNumber(weekStart);
    const startFormatted = formatDateDisplay(weekStart);
    const endFormatted = formatDateDisplay(weekEnd);

    document.getElementById('modalTitle').textContent = `New Snippet - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
    document.getElementById('snippetContent').value = '';

    showModal();
}

async function openEditModal(snippetId) {
    try {
        const response = await fetch(`/api/snippets/${snippetId}`);
        const snippet = await response.json();
        
        currentSnippetId = snippetId;
        currentWeekStart = snippet.week_start;
        currentWeekEnd = snippet.week_end;
        
        const weekNum = getWeekNumber(snippet.week_start);
        const startFormatted = formatDateDisplay(snippet.week_start);
        const endFormatted = formatDateDisplay(snippet.week_end);
        
        document.getElementById('modalTitle').textContent = `Edit Snippet - Week ${weekNum} (${startFormatted}–${endFormatted.split(',')[0]}, ${endFormatted.split(',')[1]})`;
        document.getElementById('snippetContent').value = snippet.content;
        
        showModal();
    } catch (error) {
        console.error('Error loading snippet:', error);
        alert('Failed to load snippet');
    }
}

function showModal() {
    document.getElementById('editModal').classList.add('show');
}

function closeModal() {
    document.getElementById('editModal').classList.remove('show');
    currentSnippetId = null;
}

async function saveSnippet() {
    const content = document.getElementById('snippetContent').value.trim();
    
    if (!content) {
        alert('Please enter some content');
        return;
    }
    
    try {
        let response;
        
        if (currentSnippetId) {
            // Update existing snippet
            response = await fetch(`/api/snippets/${currentSnippetId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });
        } else {
            // Create new snippet
            response = await fetch('/api/snippets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    week_start: currentWeekStart,
                    week_end: currentWeekEnd,
                    content
                })
            });
        }
        
        if (response.ok) {
            closeModal();
            await loadSnippets();
        } else {
            alert('Failed to save snippet');
        }
    } catch (error) {
        console.error('Error saving snippet:', error);
        alert('Failed to save snippet');
    }
}

function insertMarkdown(before, after = '') {
    const textarea = document.getElementById('snippetContent');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);
    
    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);
    textarea.value = newText;
    
    // Set cursor position
    const newPos = start + before.length + selectedText.length + after.length;
    textarea.focus();
    textarea.setSelectionRange(newPos, newPos);
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}


// Handle keyboard shortcuts
document.addEventListener('keydown', (e) => {
    const modal = document.getElementById('editModal');

    if (modal.classList.contains('show')) {
        if (e.key === 'Escape') {
            closeModal();
        } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            saveSnippet();
        }
    }
});

// Function to handle home navigation
function goToHome() {
    // Go to default view with 4-week range
    initializeDefaultView();
}
