/**
 * Product Tour for Next Credit
 * Uses Intro.js for interactive onboarding
 */

// Check if tour should be shown
function shouldShowTour() {
    // Check localStorage for tour completion
    const tourCompleted = localStorage.getItem('nextcredit_tour_completed');
    
    // Only show on dashboard and only if not completed
    const isDashboard = window.location.pathname === '/app' || window.location.pathname === '/dashboard';
    
    return isDashboard && !tourCompleted;
}

// Mark tour as completed
function completeTour() {
    localStorage.setItem('nextcredit_tour_completed', 'true');
    
    // Optionally send to backend for tracking
    fetch('/api/complete-tour', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    }).catch(err => console.log('Tour completion tracking failed:', err));
}

// Initialize the tour
function initTour() {
    if (!shouldShowTour()) {
        return;
    }
    
    // Wait for page to fully load
    setTimeout(() => {
        const intro = introJs();
        
        intro.setOptions({
            steps: [
                {
                    title: '👋 Welcome to Next Credit!',
                    intro: 'Let\'s take a quick tour to show you how to dispute credit report errors and track your progress.'
                },
                {
                    element: document.querySelector('.stat-card'),
                    title: '📊 Your Stats',
                    intro: 'Track your dispute progress here. See total accounts, delivered letters, and resolved disputes at a glance.',
                    position: 'bottom'
                },
                {
                    element: document.querySelector('a[href*="documents"]'),
                    title: '📄 Upload Documents',
                    intro: 'Start by uploading your credit reports here. Our AI will analyze them and help identify errors to dispute.',
                    position: 'bottom'
                },
                {
                    element: document.querySelector('a[href*="accounts"]'),
                    title: '💳 Manage Accounts',
                    intro: 'Add derogatory accounts from your credit reports. Each account can be disputed with the bureaus.',
                    position: 'bottom'
                },
                {
                    element: document.querySelector('a[href*="add-dispute"]'),
                    title: '✉️ Create Disputes',
                    intro: 'Generate AI-powered dispute letters customized for each inaccuracy. We handle the formatting and legal language.',
                    position: 'bottom'
                },
                {
                    title: '🚀 You\'re All Set!',
                    intro: 'Ready to start cleaning up your credit report? Upload your credit reports or add accounts manually to begin. You can restart this tour anytime from Settings.'
                }
            ],
            showProgress: true,
            showBullets: false,
            exitOnOverlayClick: false,
            doneLabel: 'Get Started!',
            nextLabel: 'Next →',
            prevLabel: '← Back'
        });
        
        // Handle tour completion
        intro.oncomplete(() => {
            completeTour();
        });
        
        // Handle tour exit
        intro.onexit(() => {
            completeTour();
        });
        
        // Start the tour
        intro.start();
    }, 1000); // Wait 1 second for elements to render
}

// Restart tour function (can be called from settings)
function restartTour() {
    localStorage.removeItem('nextcredit_tour_completed');
    window.location.reload();
}

// Auto-initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTour);
} else {
    initTour();
}

// Make restartTour available globally
window.restartTour = restartTour;
