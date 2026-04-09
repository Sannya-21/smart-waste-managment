// Zero2Hero - Main Application Logic

document.addEventListener('DOMContentLoaded', () => {
    // --- THEME MANAGEMENT ---
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;

    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    body.className = savedTheme;
    updateThemeIcon(savedTheme);

    themeToggle.addEventListener('click', () => {
        const newTheme = body.className === 'light' ? 'dark' : 'light';
        body.className = newTheme;
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });

    function updateThemeIcon(theme) {
        const icon = themeToggle.querySelector('i');
        icon.className = theme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
    }

    // --- CHATBOT LOGIC ---
    const chatTrigger = document.getElementById('chatTrigger');
    const chatWindow = document.getElementById('chatWindow');
    const closeChat = document.getElementById('closeChat');
    const chatInput = document.getElementById('chatInput');
    const sendChat = document.getElementById('sendChat');
    const chatMessages = document.getElementById('chatMessages');

    chatTrigger.addEventListener('click', () => {
        chatWindow.style.display = 'flex';
        chatTrigger.style.display = 'none';
    });

    closeChat.addEventListener('click', () => {
        chatWindow.style.display = 'none';
        chatTrigger.style.display = 'flex';
    });

    async function handleChat() {
        const text = chatInput.value.trim();
        if (!text) return;

        // User message
        appendMessage('user', text);
        chatInput.value = '';

        try {
            const response = await fetch(`/chat?msg=${encodeURIComponent(text)}`);
            const data = await response.json();
            appendMessage('bot', data.reply);
        } catch (e) {
            appendMessage('bot', "I'm having trouble connecting to the network. Please try again later.");
        }
    }

    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.className = `message ${sender}`;
        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendChat.addEventListener('click', handleChat);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleChat();
    });

    // --- DASHBOARD REAL-TIME LOGIC ---
    if (document.getElementById('map')) {
        initDashboard();
    }
});

let map, markers = {};

function initDashboard() {
    // Map Setup
    map = L.map('map').setView([40.730610, -73.935242], 12); // Default to NYC
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Initial Markers from server-side injected data
    const binsDataEl = document.getElementById('bins-data');
    if (binsDataEl && binsDataEl.dataset.bins) {
        try {
            const initialBins = JSON.parse(binsDataEl.dataset.bins);
            updateMarkers(initialBins);
            updateAlerts(initialBins);
        } catch (e) {
            console.error('Error parsing initial bins data:', e);
        }
    }

    // Static progress bars update
    const avgFillBar = document.getElementById('avg-fill-bar');
    if (avgFillBar && avgFillBar.dataset.fill) {
        avgFillBar.style.width = `${avgFillBar.dataset.fill}%`;
    }

    // Chart Setup
    initChart();

    // Start Polling
    setInterval(updateDashboardData, 10000); // 10 seconds
    updateDashboardData();
}

async function updateDashboardData() {
    try {
        const response = await fetch('/api/bins');
        const bins = await response.json();
        updateMarkers(bins);
        updateAlerts(bins);
    } catch (e) {
        console.error('Error fetching dashboard updates:', e);
    }
}

function updateMarkers(bins) {
    if (!bins || !Array.isArray(bins)) return;
    
    bins.forEach(bin => {
        if (!bin.lat || !bin.lng) return;
        
        const color = bin.fill > 80 ? '#ef4444' : (bin.fill > 50 ? '#fbbf24' : '#22c55e');
        
        const markerIcon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="background-color: ${color}; width: 25px; height: 25px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>`,
            iconSize: [25, 25],
            iconAnchor: [12, 12]
        });

        if (markers[bin.id]) {
            markers[bin.id].setLatLng([bin.lat, bin.lng]);
            markers[bin.id].setIcon(markerIcon);
        } else {
            const marker = L.marker([bin.lat, bin.lng], { icon: markerIcon }).addTo(map);
            marker.bindPopup(`<b>${bin.name}</b><br>Fill Level: ${bin.fill}%`);
            markers[bin.id] = marker;
        }
    });

    // Fit map to markers on first load if we have them
    const group = new L.featureGroup(Object.values(markers));
    if (group.getBounds().isValid()) {
        map.fitBounds(group.getBounds(), { padding: [50, 50] });
    }
}

function updateAlerts(bins) {
    const alertsList = document.getElementById('alertsList');
    const jsAlert = document.getElementById('jsAlert');
    if (!alertsList || !bins) return;

    const alertBins = bins.filter(b => b.fill > 80);

    if (alertBins.length > 0) {
        alertsList.innerHTML = alertBins.map(b => `
            <div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem; background: rgba(239, 68, 68, 0.05); border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.1);">
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444;"></div>
                <div style="flex: 1;">
                    <p style="font-weight: 700; font-size: 0.85rem;">${b.name}</p>
                    <p style="font-size: 0.75rem; color: var(--text-dim);">${b.fill}% capacity reached</p>
                </div>
                <a href="/collect" style="font-size: 0.75rem; color: var(--primary); font-weight: 700; text-decoration: none;">CLEAR</a>
            </div>
        `).join('');

        // Global Alert Badge for new critical alerts
        if (alertBins.some(b => b.fill > 95)) {
            jsAlert.textContent = "CRITICAL: Some bins are overflowing!";
            jsAlert.style.display = 'block';
            jsAlert.style.background = '#ef4444';
        }
    } else {
        alertsList.innerHTML = '<p style="color: var(--text-dim); font-size: 0.9rem;">No urgent alerts right now.</p>';
        jsAlert.style.display = 'none';
    }
}

function initChart() {
    const ctx = document.getElementById('wasteChart');
    if (!ctx) return;
    
    const chartCtx = ctx.getContext('2d');
    const gradient = chartCtx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.4)');
    gradient.addColorStop(1, 'rgba(34, 197, 94, 0)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Waste Collected (kg)',
                data: [65, 59, 80, 81, 56, 55, 40],
                fill: true,
                borderColor: '#22c55e',
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#22c55e',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { display: false } },
                x: { grid: { display: false } }
            }
        }
    });
}