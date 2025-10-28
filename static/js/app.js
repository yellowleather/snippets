// Global state
let currentSnippetId = null;
let currentWeekStart = null;
let currentWeekEnd = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    goToCurrentWeek();
    setupDateInputs();
    setupSearch();
});

function setupDateInputs() {
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');
    
    startInput.addEventListener('change', loadSnippets);
    endInput.addEventListener('change', loadSnippets);
}

function getWeekDates(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Monday
    
    const monday = new Date(d.setDate(diff));
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
    return date.toISOString().split('T')[0];
}

function formatDateDisplay(dateStr) {
    const date = new Date(dateStr);
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

async function goToCurrentWeek() {
    const today = new Date();
    const endWeek = getWeekDates(today);
    
    // Calculate start date (12 weeks ago)
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - (12 * 7)); // Go back 12 weeks
    const startWeek = getWeekDates(startDate);
    
    document.getElementById('startDate').value = startWeek.monday;
    document.getElementById('endDate').value = endWeek.sunday;
    
    await loadSnippets();
}

async function navigateWeek(direction) {
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');
    
    const startDate = new Date(startInput.value);
    const endDate = new Date(endInput.value);
    
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
    
    try {
        const response = await fetch(`/api/snippets?start_date=${startDate}&end_date=${endDate}`);
        const snippets = await response.json();
        
        displaySnippets(snippets);
    } catch (error) {
        console.error('Error loading snippets:', error);
    }
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
    currentWeekStart = startDate;
    currentWeekEnd = endDate;
    
    const weekNum = getWeekNumber(startDate);
    const startFormatted = formatDateDisplay(startDate);
    const endFormatted = formatDateDisplay(endDate);
    
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

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const clearButton = document.getElementById('clearSearch');
    let searchTimeout = null;
    
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        clearButton.style.display = query ? 'block' : 'none';
        
        // Update placeholder text based on input
        if (!query) {
            searchInput.placeholder = 'Search your snippets...';
        } else if (query.length < 2) {
            searchInput.placeholder = 'Enter at least 2 characters...';
        }

        // Debounce search to avoid too many requests
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        searchTimeout = setTimeout(() => {
            if (query && query.length >= 2) {  // Only search if we have 2+ characters
                searchSnippets(query);
            } else if (!query) {
                loadSnippets(); // Load normal date-based view
            }
        }, 300);
    });

    // Handle special keys
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            searchInput.value = '';
            clearButton.style.display = 'none';
            loadSnippets();
        }
    });

    clearButton.addEventListener('click', () => {
        searchInput.value = '';
        clearButton.style.display = 'none';
        searchInput.placeholder = 'Search your snippets...';
        loadSnippets(); // Load normal date-based view
    });
}

async function searchSnippets(query) {
    try {
        const response = await fetch(`/api/snippets/search?q=${encodeURIComponent(query)}`);
        const snippets = await response.json();
        displaySnippets(snippets);
    } catch (error) {
        console.error('Error searching snippets:', error);
    }
}

// Handle keyboard shortcuts
document.addEventListener('keydown', (e) => {
    const modal = document.getElementById('editModal');
    const searchInput = document.getElementById('searchInput');
    
    if (modal.classList.contains('show')) {
        if (e.key === 'Escape') {
            closeModal();
        } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            saveSnippet();
        }
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        // Quick search shortcut
        e.preventDefault();
        searchInput.focus();
    }
});

// Function to handle home navigation
function goToHome() {
    // Clear search if any
    const searchInput = document.getElementById('searchInput');
    const clearButton = document.getElementById('clearSearch');
    searchInput.value = '';
    clearButton.style.display = 'none';
    
    // Go to current week view with default 12-week range
    goToCurrentWeek();
}
