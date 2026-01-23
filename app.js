const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8000/api' : '/api';
let token = localStorage.getItem('token');
let currentUser = null;
let activeGroupId = null;

// DOM Elements
const app = document.getElementById('app');
const authScreen = document.getElementById('auth-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const authError = document.getElementById('auth-error');
const groupList = document.getElementById('group-list');
const messageList = document.getElementById('message-list');
const chatContainer = document.getElementById('chat-container');
const noChatSelected = document.getElementById('no-chat-selected');
const activeGroupName = document.getElementById('active-group-name');
const activeGroupDesc = document.getElementById('active-group-desc');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const createGroupBtn = document.getElementById('create-group-btn');
const createGroupModal = document.getElementById('create-group-modal');
const createGroupForm = document.getElementById('create-group-form');
const closeModal = document.querySelector('.close-modal');
const currentUsernameDisplay = document.getElementById('current-username');

// Initialization
async function init() {
    if (token) {
        try {
            await fetchCurrentUser();
            showDashboard();
        } catch (e) {
            logout();
        }
    } else {
        showAuth();
    }
}

// Auth Functions
function showAuthTab(tab) {
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    if (tab === 'login') {
        document.getElementById('login-form').classList.add('active');
        document.querySelector('.tab-btn:first-child').classList.add('active');
    } else {
        document.getElementById('register-form').classList.add('active');
        document.querySelector('.tab-btn:last-child').classList.add('active');
    }
    authError.textContent = '';
}

async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API_URL}/token`, {
        method: 'POST',
        body: formData
    });

    if (!res.ok) throw new Error('Invalid credentials');

    const data = await res.json();
    token = data.access_token;
    localStorage.setItem('token', token);
    await fetchCurrentUser();
    showDashboard();
}

async function register(username, email, password, isSenior) {
    const res = await fetch(`${API_URL}/users/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password, is_senior: isSenior })
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
    }

    // Auto login
    await login(username, password);
}

async function fetchCurrentUser() {
    const res = await fetch(`${API_URL}/users/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Session expired');
    currentUser = await res.json();
    currentUsernameDisplay.textContent = currentUser.username;

    // Toggle Create Group button visibility (Only Seniors)
    if (currentUser.is_senior) {
        createGroupBtn.style.display = 'block';
    } else {
        createGroupBtn.style.display = 'none';
    }

    fetchGroups();
}

function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
    showAuth();
}

function showAuth() {
    authScreen.classList.add('active');
    dashboardScreen.classList.remove('active');
}

function showDashboard() {
    authScreen.classList.remove('active');
    dashboardScreen.classList.add('active');
}

// Group Functions
async function fetchGroups() {
    const res = await fetch(`${API_URL}/groups/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const groups = await res.json();
    renderGroups(groups);
}

function renderGroups(groups) {
    groupList.innerHTML = '';
    groups.forEach(group => {
        const li = document.createElement('li');
        li.className = `group-item ${group.id === activeGroupId ? 'active' : ''}`;
        li.textContent = group.name;
        li.onclick = () => selectGroup(group);
        groupList.appendChild(li);
    });
}

async function createGroup(name, description) {
    const res = await fetch(`${API_URL}/groups/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name, description })
    });

    if (!res.ok) {
        alert('Failed to create group. Are you a senior?');
        return;
    }

    createGroupModal.classList.remove('active');
    fetchGroups();
}

function selectGroup(group) {
    activeGroupId = group.id;
    activeGroupName.textContent = group.name;
    activeGroupDesc.textContent = group.description || '';

    document.querySelectorAll('.group-item').forEach(el => el.classList.remove('active'));
    // Re-render would fix class logic or just do manual toggle, fetchGroups overkill
    fetchGroups(); // Lazy update for Highlight

    noChatSelected.style.display = 'none';
    chatContainer.classList.remove('hidden');
    loadMessages(group.id);
}

// Chat Functions
async function loadMessages(groupId) {
    const res = await fetch(`${API_URL}/groups/${groupId}/messages/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const messages = await res.json();
    renderMessages(messages);
}

function renderMessages(messages) {
    messageList.innerHTML = '';
    messages.forEach(msg => {
        const div = document.createElement('div');
        // We need sender info. The API returns sender_id.
        // In a real app we'd map ID to Name or expand the response.
        // For now, let's just show "User ID" or fix API.
        // Assuming backend logic returns basic Message object.
        // Let's assume current user is sender for styling.
        const isMe = msg.sender_id === currentUser.id;

        div.className = `message ${isMe ? 'sent' : 'received'}`;

        let senderName = `User ${msg.sender_id}`; // Basic fallback
        if (isMe) senderName = 'You';

        div.innerHTML = `
            <span class="message-sender">${senderName}</span>
            ${msg.content}
        `;
        messageList.appendChild(div);
    });
    messageList.scrollTop = messageList.scrollHeight;
}

async function sendMessage(content) {
    if (!activeGroupId) return;

    await fetch(`${API_URL}/groups/${activeGroupId}/messages/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content, group_id: activeGroupId })
    });

    messageInput.value = '';
    loadMessages(activeGroupId);
}

// Event Listeners
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    try {
        await login(username, password);
    } catch (err) {
        authError.textContent = err.message;
    }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const isSenior = document.getElementById('reg-senior').checked;

    try {
        await register(username, email, password, isSenior);
    } catch (err) {
        authError.textContent = err.message;
    }
});

createGroupBtn.addEventListener('click', () => {
    createGroupModal.classList.add('active');
});

closeModal.addEventListener('click', () => {
    createGroupModal.classList.remove('active');
});

createGroupForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('group-name').value;
    const desc = document.getElementById('group-desc').value;
    createGroup(name, desc);
});

messageForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const content = messageInput.value;
    if (content.trim()) sendMessage(content);
});

// Polling for messages (Simple real-time simulation)
setInterval(() => {
    if (activeGroupId) loadMessages(activeGroupId);
}, 3000);

init();
