const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

// Form and error message references
const registerForm = document.getElementById('register-form');
const loginForm = document.getElementById('login-form');
const registerErrorMsg = document.getElementById('register-error-message');
const loginErrorMsg = document.getElementById('login-error-message');

// --- Utility Functions ---

/** Displays an error message and logs it to the console. */
function displayError(element, message) {
    element.textContent = message;
    console.error(message);
}

/** Clears the error message display. */
function clearError(element) {
    element.textContent = '';
}

/** Navigates the user to the chat page and stores the login status. */
function completeLogin(username, isAdmin) {
    console.log(`Login successful for user: ${username}. Admin: ${isAdmin}`);
    // Store user info in localStorage to persist login state 
    localStorage.setItem('currentUser', JSON.stringify({ username: username, isAdmin: isAdmin }));
    
    // Redirect to the main chat page
    window.location.href = 'chatindex.html'; 
}


// --- Event Listeners for UI animation ---

registerBtn.addEventListener('click', () => {
    container.classList.add('active');
    clearError(loginErrorMsg);
});

loginBtn.addEventListener('click', () => {
    container.classList.remove('active');
    clearError(registerErrorMsg);
});


// --- Registration Handler ---

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError(registerErrorMsg);

    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch('http://localhost:5000/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Success: Switch to login form
            displayError(registerErrorMsg, "Registration successful! Please log in.");
            container.classList.remove('active'); // Switch to login view
            clearError(loginErrorMsg);
        } else {
            // Failure: Display error message from backend
            displayError(registerErrorMsg, result.message || "Registration failed.");
        }

    } catch (error) {
        displayError(registerErrorMsg, "Network error: Could not reach the server.");
    }
});


// --- Login Handler ---

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError(loginErrorMsg);

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('http://localhost:5000/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const result = await response.json();

        if (response.ok && result.success) {
            // Success: Redirect to chat page
            completeLogin(result.username, result.isAdmin);
        } else {
            // Failure: Display error message from backend
            displayError(loginErrorMsg, result.message || "Invalid email or password.");
        }

    } catch (error) {
        displayError(loginErrorMsg, "Network error: Could not reach the server.");
    }
});


// --- Initial Auth State Check (To prevent re-login) ---
window.addEventListener('load', () => {
    // Check if user has a local storage token from a previous session
    const loggedInUser = localStorage.getItem('currentUser');
    if (loggedInUser && window.location.pathname.endsWith('login.html')) {
         console.log("User found in storage. Redirecting to chat...");
         window.location.href = 'chatindex.html';
         return;
    }
});
