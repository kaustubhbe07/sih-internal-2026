// Automatically detect if running locally vs deployed (Unified Deployment)
const API_BASE_URL = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
    ? 'http://127.0.0.1:8001' 
    : window.location.origin;

// --- TOAST NOTIFICATIONS ---
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // SVG icons based on type
    const iconSvg = type === 'success' 
        ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
        : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;

    toast.innerHTML = `
        <div class="toast-icon">${iconSvg}</div>
        <div class="toast-message">${message}</div>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove
    const removeToast = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400); // Wait for transition
    };

    let timer = setTimeout(removeToast, 4000);

    // Close button
    toast.querySelector('.toast-close').onclick = () => {
        clearTimeout(timer);
        removeToast();
    };
}

let currentMode = "login";

// Check if arrived via signup link
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get("signup") === "true") {
    switchMode("signup");
}

function switchMode(mode) {
    currentMode = mode;
    const signupFields = document.querySelector(".signup-fields");
    const btn = document.getElementById("submitBtn");
    const footer = document.getElementById("form-footer");

    document.getElementById("tab-login").classList.remove("active");
    document.getElementById("tab-signup").classList.remove("active");
    document.getElementById("tab-" + mode).classList.add("active");

    if (mode === "signup") {
        signupFields.style.display = "block";
        document.getElementById("instName").setAttribute("required", "true");
        btn.textContent = "Create Account";
        footer.innerHTML = 'Already have an account? <a href="#" onclick="switchMode(\'login\'); return false;">Log in</a>';
    } else {
        signupFields.style.display = "none";
        document.getElementById("instName").removeAttribute("required");
        btn.textContent = "Sign In";
        footer.innerHTML = 'Don\'t have an account? <a href="#" onclick="switchMode(\'signup\'); return false;">Sign up here</a>';
    }
}

async function handleAuth(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const btn = document.getElementById('submitBtn');
    
    // Disable button to prevent double clicks
    const originalText = btn.textContent;
    btn.textContent = 'Please wait...';
    btn.disabled = true;

    try {
        if (currentMode === 'signup') {
            const instName = document.getElementById('instName').value;
            const payload = {
                name: instName,
                email: email,
                password: password
                // We'll leave field_schema empty for now, or add UI for it later
            };

            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Registration successful! Please log in.', 'success');
                switchMode('login');
                document.getElementById('password').value = '';
            } else {
                showToast(`Registration failed: ${data.detail || 'Unknown error'}`, 'error');
            }

        } else {
            // Login Mode
            const payload = {
                email: email,
                password: password
            };

            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                // Save the JWT token and institution details
                localStorage.setItem('certify_token', data.access_token);
                localStorage.setItem('certify_inst_name', data.institution_name);
                localStorage.setItem('certify_inst_id', data.institution_id);
                // Redirect to dashboard
                window.location.href = "dashboard.html";
            } else {
                showToast(`Login failed: ${data.detail || 'Invalid credentials'}`, 'error');
            }
        }
    } catch (error) {
        console.error('Error during auth:', error);
        showToast('A network error occurred. Please make sure the backend is running.', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
