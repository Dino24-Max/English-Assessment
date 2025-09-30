// ============================================================================
// CCL English Assessment Platform - JavaScript Module
// ============================================================================
// Extracted from ui_application.py
// Contains all client-side functionality for the assessment platform
// ============================================================================

// ============================================================================
// GLOBAL STATE MANAGEMENT
// ============================================================================
let selectedAnswer = '';

// ============================================================================
// CORE ANSWER SELECTION FUNCTIONS
// ============================================================================

/**
 * Handles answer selection for multiple choice questions
 * @param {string} answer - The selected answer text
 * @param {HTMLElement} element - The DOM element that was clicked
 */
function selectAnswer(answer, element) {
    selectedAnswer = answer;
    document.getElementById('submitBtn').disabled = false;
    if (element) {
        document.querySelectorAll('.option').forEach(opt => opt.classList.remove('selected'));
        element.classList.add('selected');
    }
}

/**
 * Submits the current answer and navigates to next question
 * @param {number} qNum - Current question number
 */
function submitAnswer(qNum) {
    if (!selectedAnswer.trim()) {
        alert('Please provide an answer before continuing');
        return;
    }

    // Show loading state
    document.getElementById('submitBtn').innerHTML = 'Processing...';
    document.getElementById('submitBtn').disabled = true;

    // Add slight delay for better UX
    setTimeout(() => {
        window.location.href = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;
    }, 500);
}

// ============================================================================
// LISTENING MODULE - Audio Playback with Replay Limit
// ============================================================================

let replaysLeft = 2;

/**
 * Plays audio using text-to-speech for listening comprehension questions
 * Tracks replay count and provides visual feedback
 */
function playAudio() {
    if (replaysLeft <= 0) {
        document.getElementById('audioStatus').innerHTML = '<span class="status-error">❌ No more replays</span>';
        return;
    }
    const utterance = new SpeechSynthesisUtterance(audioText);
    utterance.rate = 0.8;
    utterance.onstart = () => {
        document.getElementById('audioStatus').innerHTML = '<span class="status-playing">🔊 Playing audio...</span>';
        document.getElementById('playBtn').style.opacity = '0.7';
    };
    utterance.onend = () => {
        replaysLeft--;
        document.getElementById('audioStatus').innerHTML = '<span class="status-complete">✅ Audio complete</span>';
        document.getElementById('replayInfo').innerHTML = replaysLeft > 0 ? replaysLeft + ' replay(s) remaining' : 'No more replays available';
        document.getElementById('playBtn').style.opacity = '1';
    };
    speechSynthesis.speak(utterance);
}

// ============================================================================
// TIME & NUMBERS MODULE - Audio Context Questions
// ============================================================================

/**
 * Plays conversation audio for time and numbers questions
 * Simpler version without replay limits for information extraction tasks
 */
function playAudioTimeNumbers() {
    const utterance = new SpeechSynthesisUtterance(audioText);
    utterance.rate = 0.8;
    utterance.onstart = () => document.getElementById('audioStatus').innerHTML = '<span class="status-playing">🔊 Playing conversation...</span>';
    utterance.onend = () => document.getElementById('audioStatus').innerHTML = '<span class="status-complete">✅ Conversation complete</span>';
    speechSynthesis.speak(utterance);
}

// ============================================================================
// VOCABULARY MODULE - Drag and Drop Matching
// ============================================================================

let matches = {};
let draggedTerm = null;
let correctMatches = {}; // Will be populated by template

/**
 * Handles drag start event for vocabulary terms
 * @param {DragEvent} e - The drag event
 * @param {string} term - The term being dragged
 */
function dragStart(e, term) {
    draggedTerm = term;
    e.dataTransfer.effectAllowed = 'move';
    e.target.style.opacity = '0.5';
}

/**
 * Handles drag end event
 * @param {DragEvent} e - The drag event
 */
function dragEnd(e) {
    e.target.style.opacity = '1';
}

/**
 * Allows drop on definition targets
 * @param {DragEvent} e - The drag event
 */
function allowDrop(e) {
    e.preventDefault();
}

/**
 * Handles drop event when term is dropped on definition
 * @param {DragEvent} e - The drag event
 * @param {string} definition - The target definition
 */
function drop(e, definition) {
    e.preventDefault();
    if (draggedTerm) {
        matches[draggedTerm] = definition;
        updateMatchesDisplay();
        checkAllMatched();
        e.target.classList.remove('drag-over');
    }
}

/**
 * Updates the visual display of current matches
 */
function updateMatchesDisplay() {
    const matchesList = document.getElementById('matchesList');
    matchesList.innerHTML = '';
    for (const [term, def] of Object.entries(matches)) {
        const matchDiv = document.createElement('div');
        matchDiv.className = 'match-item';
        matchDiv.innerHTML = `
            <span class="match-term">${term}</span>
            <span class="match-arrow">→</span>
            <span class="match-def">${def}</span>
            <button onclick="removeMatch('${term}')" class="remove-btn">×</button>
        `;
        matchesList.appendChild(matchDiv);
    }
}

/**
 * Removes a match from the vocabulary matching
 * @param {string} term - The term to remove from matches
 */
function removeMatch(term) {
    delete matches[term];
    updateMatchesDisplay();
    checkAllMatched();
}

/**
 * Checks if all terms have been matched and enables submit button
 */
function checkAllMatched() {
    const allMatched = Object.keys(matches).length === termsCount;
    document.getElementById('submitBtn').disabled = !allMatched;
    if (allMatched) {
        selectedAnswer = JSON.stringify(matches);
    }
}

// ============================================================================
// SPEAKING MODULE - Voice Recording with Analysis
// ============================================================================

let mediaRecorder;
let recordingSeconds = 0;
let speechDetected = false;
let recordingInterval;
let minDuration = 5; // Will be set by template

/**
 * Starts voice recording for speaking assessment
 * Uses Web Audio API to detect speech and validate recording
 */
function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        recordingSeconds = 0;
        speechDetected = false;

        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        source.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkAudio = () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                analyser.getByteFrequencyData(dataArray);
                const volume = dataArray.reduce((sum, val) => sum + val) / bufferLength;
                if (volume > 10) speechDetected = true;
                requestAnimationFrame(checkAudio);
            }
        };
        checkAudio();

        mediaRecorder.onstart = () => {
            document.getElementById('recordingStatus').innerHTML = '<span class="status-recording">🎤 Recording in progress... Speak now!</span>';
            document.getElementById('recordBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;

            recordingInterval = setInterval(() => {
                recordingSeconds++;
                document.getElementById('recordingStatus').innerHTML = `<span class="status-recording">🎤 Recording... ${recordingSeconds}s</span>`;
                if (recordingSeconds >= 30) {
                    clearInterval(recordingInterval);
                    stopRecording();
                }
            }, 1000);
        };

        mediaRecorder.onstop = () => {
            clearInterval(recordingInterval);
            document.getElementById('recordBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;

            if (!speechDetected) {
                selectedAnswer = 'No speech detected';
                document.getElementById('recordingStatus').innerHTML = '<span class="status-error">❌ No speech detected - Please try again</span>';
            } else if (recordingSeconds < minDuration) {
                selectedAnswer = `Too short: ${recordingSeconds}s`;
                document.getElementById('recordingStatus').innerHTML = `<span class="status-warning">⚠️ Recording too short (${recordingSeconds}s) - Minimum ${minDuration}s required</span>`;
            } else {
                selectedAnswer = `Speech recorded: ${recordingSeconds}s`;
                document.getElementById('recordingStatus').innerHTML = `<span class="status-success">✅ Excellent recording (${recordingSeconds}s) - Ready to submit</span>`;
            }

            document.getElementById('submitBtn').disabled = false;
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
    })
    .catch(err => {
        document.getElementById('recordingStatus').innerHTML = '<span class="status-error">❌ Microphone access denied - Please allow microphone access</span>';
    });
}

/**
 * Stops the current voice recording
 */
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Sets audio text for text-to-speech functions
 * Called from inline scripts with question-specific audio
 * @param {string} text - The text to be spoken
 */
function setAudioText(text) {
    window.audioText = text;
}

/**
 * Sets the number of terms for vocabulary matching validation
 * @param {number} count - Number of terms to match
 */
function setTermsCount(count) {
    window.termsCount = count;
}

/**
 * Sets minimum duration for speaking module
 * @param {number} duration - Minimum recording duration in seconds
 */
function setMinDuration(duration) {
    window.minDuration = duration;
}

/**
 * Sets correct matches for vocabulary validation
 * @param {Object} matches - Object mapping terms to correct definitions
 */
function setCorrectMatches(matchesObj) {
    window.correctMatches = matchesObj;
}

// ============================================================================
// LOADING INDICATOR FUNCTIONS
// ============================================================================

/**
 * Shows a full-page loading overlay with optional custom message
 * @param {string} message - Primary loading message
 * @param {string} subtext - Secondary loading message (optional)
 */
function showLoading(message = 'Processing', subtext = 'Please wait...') {
    // Remove existing overlay if present
    hideLoading();

    // Create loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loadingOverlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <div class="loading-text">${message}</div>
            <div class="loading-subtext">${subtext}</div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Trigger animation
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

/**
 * Hides the loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

/**
 * Adds loading state to a specific button
 * @param {HTMLElement|string} button - Button element or ID
 */
function setButtonLoading(button) {
    const btn = typeof button === 'string' ? document.getElementById(button) : button;
    if (btn) {
        btn.classList.add('btn-loading');
        btn.disabled = true;
        btn.dataset.originalText = btn.innerHTML;
    }
}

/**
 * Removes loading state from a specific button
 * @param {HTMLElement|string} button - Button element or ID
 * @param {string} newText - Optional new text to display (uses original if not provided)
 */
function removeButtonLoading(button, newText = null) {
    const btn = typeof button === 'string' ? document.getElementById(button) : button;
    if (btn) {
        btn.classList.remove('btn-loading');
        btn.disabled = false;
        btn.innerHTML = newText || btn.dataset.originalText || btn.innerHTML;
    }
}

// ============================================================================
// ERROR HANDLING & NOTIFICATION FUNCTIONS
// ============================================================================

/**
 * Displays an error message notification
 * @param {string} title - Error title
 * @param {string} message - Error message body
 * @param {number} duration - Auto-hide duration in ms (0 = no auto-hide)
 * @param {Function} retryCallback - Optional retry function
 */
function showError(title, message, duration = 5000, retryCallback = null) {
    showNotification('error', title, message, duration, retryCallback);
}

/**
 * Displays a success message notification
 * @param {string} title - Success title
 * @param {string} message - Success message body
 * @param {number} duration - Auto-hide duration in ms
 */
function showSuccess(title, message, duration = 3000) {
    showNotification('success', title, message, duration);
}

/**
 * Displays a warning message notification
 * @param {string} title - Warning title
 * @param {string} message - Warning message body
 * @param {number} duration - Auto-hide duration in ms
 */
function showWarning(title, message, duration = 4000) {
    showNotification('warning', title, message, duration);
}

/**
 * Generic notification display function
 * @param {string} type - Notification type: 'error', 'success', 'warning'
 * @param {string} title - Notification title
 * @param {string} message - Notification message
 * @param {number} duration - Auto-hide duration in ms
 * @param {Function} retryCallback - Optional retry function
 */
function showNotification(type, title, message, duration = 3000, retryCallback = null) {
    // Remove any existing notifications
    document.querySelectorAll('.error-message, .success-message, .warning-message').forEach(el => el.remove());

    const icons = {
        error: '❌',
        success: '✅',
        warning: '⚠️'
    };

    const notification = document.createElement('div');
    notification.className = `${type}-message`;
    notification.innerHTML = `
        <div class="message-header">
            <span class="message-icon">${icons[type]}</span>
            <span class="message-title">${title}</span>
        </div>
        <div class="message-body">${message}</div>
        ${retryCallback ? '<div class="message-actions"><button class="retry-btn" onclick="handleRetry()">Retry</button></div>' : ''}
        <button class="message-close" onclick="closeNotification(this)">×</button>
    `;

    document.body.appendChild(notification);

    // Store retry callback if provided
    if (retryCallback) {
        window._currentRetryCallback = retryCallback;
    }

    // Trigger animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto-hide after duration (if > 0)
    if (duration > 0) {
        setTimeout(() => {
            closeNotification(notification);
        }, duration);
    }
}

/**
 * Closes a notification message
 * @param {HTMLElement} element - Notification element or close button
 */
function closeNotification(element) {
    const notification = element.classList.contains('message-close') ? element.parentElement : element;
    notification.classList.remove('show');
    notification.classList.add('hide');
    setTimeout(() => {
        notification.remove();
    }, 400);
}

/**
 * Handles retry action from error notifications
 */
function handleRetry() {
    if (window._currentRetryCallback && typeof window._currentRetryCallback === 'function') {
        window._currentRetryCallback();
        window._currentRetryCallback = null;
    }
}

/**
 * Handles API errors and displays appropriate messages
 * @param {Error|Response} error - Error object or fetch response
 * @param {string} context - Context of where the error occurred
 * @param {Function} retryCallback - Optional retry function
 */
function handleAPIError(error, context = 'Operation', retryCallback = null) {
    hideLoading();

    let title = 'Error';
    let message = 'An unexpected error occurred. Please try again.';

    // Handle different error types
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        title = 'Network Error';
        message = 'Unable to connect to the server. Please check your internet connection and try again.';
    } else if (error.status === 404) {
        title = 'Not Found';
        message = 'The requested resource was not found.';
    } else if (error.status === 500) {
        title = 'Server Error';
        message = 'The server encountered an error. Please try again in a moment.';
    } else if (error.status === 403) {
        title = 'Access Denied';
        message = 'You do not have permission to perform this action.';
    } else if (error.message) {
        message = error.message;
    }

    showError(title, `${context}: ${message}`, 0, retryCallback);
    console.error(`${context} Error:`, error);
}

/**
 * Validates network connection
 * @returns {boolean} True if online, false otherwise
 */
function isOnline() {
    return navigator.onLine;
}

/**
 * Monitors network status and shows/hides offline warning
 */
function monitorNetworkStatus() {
    window.addEventListener('online', function() {
        showSuccess('Connection Restored', 'You are back online!');
    });

    window.addEventListener('offline', function() {
        showWarning('No Internet Connection', 'Please check your network connection. Changes may not be saved.', 0);
    });
}

// ============================================================================
// ENHANCED FORM SUBMISSION WITH ERROR HANDLING
// ============================================================================

/**
 * Enhanced submit answer function with loading states and error handling
 * @param {number} qNum - Current question number
 */
function submitAnswerWithLoading(qNum) {
    // Validate answer
    if (!selectedAnswer.trim()) {
        showWarning('Answer Required', 'Please provide an answer before continuing.');
        return;
    }

    // Check network connection
    if (!isOnline()) {
        showError('No Connection', 'Please check your internet connection before submitting.', 0, () => submitAnswerWithLoading(qNum));
        return;
    }

    // Show loading state
    const submitBtn = document.getElementById('submitBtn');
    setButtonLoading(submitBtn);
    showLoading('Submitting Answer', 'Processing your response...');

    // Create retry callback
    const retrySubmit = () => submitAnswerWithLoading(qNum);

    // Use fetch API for better error handling
    const url = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;

    fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'text/html'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.text();
    })
    .then(() => {
        // Success - navigate to the response
        window.location.href = url;
    })
    .catch(error => {
        // Error handling
        removeButtonLoading(submitBtn, 'Submit Answer');
        handleAPIError(error, 'Submission failed', retrySubmit);
    });
}

// ============================================================================
// NETWORK ERROR RECOVERY
// ============================================================================

/**
 * Retry mechanism with exponential backoff
 * @param {Function} operation - Function to retry
 * @param {number} maxRetries - Maximum number of retry attempts
 * @param {number} delay - Initial delay in ms
 */
async function retryWithBackoff(operation, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await operation();
        } catch (error) {
            if (i === maxRetries - 1) throw error;

            const waitTime = delay * Math.pow(2, i);
            console.log(`Retry attempt ${i + 1} failed. Waiting ${waitTime}ms before next retry...`);

            await new Promise(resolve => setTimeout(resolve, waitTime));
        }
    }
}

/**
 * Safe fetch wrapper with automatic retry and error handling
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @param {number} maxRetries - Maximum retry attempts
 * @returns {Promise<Response>} Fetch response
 */
async function safeFetch(url, options = {}, maxRetries = 3) {
    return retryWithBackoff(async () => {
        if (!isOnline()) {
            throw new Error('No internet connection');
        }

        const response = await fetch(url, {
            ...options,
            timeout: 10000 // 10 second timeout
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response;
    }, maxRetries);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('CCL Assessment Platform JavaScript loaded');

    // Reset selected answer on page load
    selectedAnswer = '';

    // Disable submit button by default
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
    }

    // Initialize network monitoring
    monitorNetworkStatus();

    // Add global error handler
    window.addEventListener('error', function(event) {
        console.error('Global error caught:', event.error);
    });

    // Add unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        handleAPIError(event.reason, 'An unexpected error occurred');
    });

    // Check initial network status
    if (!isOnline()) {
        showWarning('No Internet Connection', 'You are currently offline. Some features may not work.', 0);
    }
});
