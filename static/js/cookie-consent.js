/**
 * Cookie Consent Banner for Next Credit
 * GDPR/CCPA compliant with PostHog analytics integration
 */

(function() {
    'use strict';
    
    const CONSENT_KEY = 'nextcredit_cookie_consent';
    const CONSENT_VERSION = '1.0'; // Increment when policy changes
    
    /**
     * Check if user has already given consent
     */
    function hasConsent() {
        try {
            const consent = localStorage.getItem(CONSENT_KEY);
            if (!consent) return null;
            
            const data = JSON.parse(consent);
            // Check if consent is current version
            if (data.version === CONSENT_VERSION) {
                return data.accepted;
            }
            return null; // Show banner again if version changed
        } catch (e) {
            return null;
        }
    }
    
    /**
     * Save user's consent choice
     */
    function saveConsent(accepted) {
        const data = {
            accepted: accepted,
            version: CONSENT_VERSION,
            timestamp: new Date().toISOString()
        };
        localStorage.setItem(CONSENT_KEY, JSON.stringify(data));
        
        // Initialize PostHog if user accepts
        if (accepted && typeof window.posthog !== 'undefined') {
            initializePostHog();
        } else if (!accepted && typeof window.posthog !== 'undefined') {
            // Disable PostHog if user declines
            window.posthog.opt_out_capturing();
        }
    }
    
    /**
     * Initialize PostHog analytics (only if consent given)
     */
    function initializePostHog() {
        // PostHog will be initialized here when you add the API key
        // Example:
        // posthog.init('YOUR_API_KEY', {
        //     api_host: 'https://app.posthog.com',
        //     loaded: function(posthog) {
        //         console.log('PostHog initialized');
        //     }
        // });
        console.log('Analytics enabled - PostHog ready to initialize');
    }
    
    /**
     * Create and show cookie consent banner
     */
    function showConsentBanner() {
        const banner = document.createElement('div');
        banner.id = 'cookie-consent-banner';
        banner.innerHTML = `
            <div class="cookie-consent-content">
                <div class="cookie-consent-text">
                    <p>
                        <strong>🍪 We use cookies</strong><br>
                        We use essential cookies for authentication and optional analytics cookies to improve your experience.
                        <a href="/cookie-policy" target="_blank" class="cookie-policy-link">Learn more</a>
                    </p>
                </div>
                <div class="cookie-consent-buttons">
                    <button id="cookie-accept" class="btn btn-primary btn-sm">
                        Accept All
                    </button>
                    <button id="cookie-decline" class="btn btn-outline-secondary btn-sm">
                        Essential Only
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        // Add event listeners
        document.getElementById('cookie-accept').addEventListener('click', function() {
            saveConsent(true);
            hideBanner();
        });
        
        document.getElementById('cookie-decline').addEventListener('click', function() {
            saveConsent(false);
            hideBanner();
        });
        
        // Show banner with animation
        setTimeout(function() {
            banner.classList.add('show');
        }, 500);
    }
    
    /**
     * Hide and remove banner
     */
    function hideBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (banner) {
            banner.classList.remove('show');
            setTimeout(function() {
                banner.remove();
            }, 300);
        }
    }
    
    /**
     * Initialize on page load
     */
    document.addEventListener('DOMContentLoaded', function() {
        const consent = hasConsent();
        
        if (consent === null) {
            // No consent stored, show banner
            showConsentBanner();
        } else if (consent === true) {
            // User accepted, initialize analytics
            if (typeof window.posthog !== 'undefined') {
                initializePostHog();
            }
        }
        // If consent === false, do nothing (essential cookies only)
    });
})();
