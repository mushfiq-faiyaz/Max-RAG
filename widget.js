(function() {
    const API_URL = "http://127.0.0.1:8000/chat"; 
    const STREAM_URL = "http://127.0.0.1:8000/chat/stream";
    const CONFIG_URL = API_URL.replace('/chat', '/config'); 
    const LEAD_URL = API_URL.replace('/chat', '/lead');
    const FEEDBACK_URL = API_URL.replace('/chat', '/api/feedback');
    const AUTH_TOKEN = "my_secret_token_123";
    
    let CLIENT_NAME = "Pall Mall Dental";
    let QUICK_ACTIONS = ["Book Appointment", "Treatment Pricing", "Emergency Dentist", "Opening Hours"];
    let WELCOME_MESSAGE = "Hi! How can I help you today?";
    let INSTANT_ANSWERS = {}; 
    
    let PRIMARY_COLOR = "#1A1A1A"; 
    let ACCENT_COLOR = "#C0A060"; 
    let BOOKING_URL = "#";
    const IS_DEMO = true; 
    const TERMS_URL = "https://your-terms-link.com"; 

    const MAX_SESSION_LIMIT = 12;
    const MAX_DAILY_LIMIT = 8;
    let sessionCount = 0;
    let chatLog = []; 
    let conversationHistory = [];
    let isTypingGreeting = false; 
    let userMessageCount = 0;
    
    let leadData = {};

    const emergencyKeywords = ["bleed", "bleeding", "severe pain", "swelling", "can't swallow", "trouble swallowing", "can't breathe", "knocked out", "broken tooth", "fell out", "trauma", "abscess"];

    const iconChat = `<svg viewBox="0 0 24 24" fill="currentColor" style="width:24px; height:24px;"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>`;
    const iconClose = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" style="width:20px; height:20px; display:block;"><path d="M18 6L6 18M6 6l12 12"/></svg>`;
    const iconRefresh = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:18px; height:18px; display:block;"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path></svg>`;
    const iconSend = `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px;"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>`;
    const iconThumbUp = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>`;
    const iconThumbDown = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path></svg>`;

    function getBotAvatar() {
        return `<div style="width:24px; height:24px; background:${ACCENT_COLOR}; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-size:12px; font-weight:bold; flex-shrink:0;">P</div>`;
    }
    let botAvatar = getBotAvatar();

    fetch(CONFIG_URL)
        .then(res => res.json())
        .then(data => {
            if (data.client_name) CLIENT_NAME = data.client_name;
            if (data.quick_actions) QUICK_ACTIONS = data.quick_actions;
            if (data.welcome_message) WELCOME_MESSAGE = data.welcome_message;
            if (data.instant_answers) INSTANT_ANSWERS = data.instant_answers; 
            if (data.branding) {
                if (data.branding.primary_color) PRIMARY_COLOR = data.branding.primary_color;
                if (data.branding.accent_color) ACCENT_COLOR = data.branding.accent_color;
                if (data.branding.booking_url) BOOKING_URL = data.branding.booking_url;
                botAvatar = getBotAvatar();
            }
            initWidget();
        })
        .catch(err => {
            console.log("Using default config", err);
            initWidget();
        });

    function initWidget() {
        const style = document.createElement('style');
        style.innerHTML = `
            #lr-widget-container * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; -webkit-font-smoothing: antialiased; letter-spacing: normal; word-spacing: normal; -webkit-tap-highlight-color: transparent; outline: none; }
            #lr-chat-btn { position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px; background: ${PRIMARY_COLOR}; border-radius: 50%; border: 2px solid ${ACCENT_COLOR}; cursor: pointer; box-shadow: 0 8px 24px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.2s; z-index: 999999; color: ${ACCENT_COLOR}; }
            #lr-chat-btn:active { transform: scale(0.92); opacity: 0.8; }
            #lr-chat-btn:hover { transform: scale(1.06) translateY(-2px); }
            #lr-chat-btn svg { transition: transform 0.3s ease; }
            #lr-chat-btn.lr-active svg { transform: rotate(90deg); }
            #lr-chat-window { position: fixed; bottom: 80px; right: 24px; width: 380px; height: 600px; max-height: calc(100vh - 110px); background: rgba(255, 255, 255, 0.98); backdrop-filter: blur(24px); border-radius: 18px; box-shadow: 0 24px 48px -12px rgba(0,0,0,0.25); display: none; flex-direction: column; overflow: hidden; z-index: 999999; }
            #lr-chat-window.lr-open { display: flex; animation: lr-popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
            @keyframes lr-popIn { 0% { opacity: 0; transform: scale(0.92) translateY(20px); } 100% { opacity: 1; transform: scale(1) translateY(0); } }
            #lr-header { background: ${PRIMARY_COLOR}; color: ${ACCENT_COLOR}; padding: 14px 16px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; font-size: 15px; border-bottom: 2px solid ${ACCENT_COLOR}; }
            .lr-header-actions { display: flex; gap: 12px; align-items: center; }
            #lr-reset, #lr-close { background: none; border: none; cursor: pointer; padding: 0; display: flex; align-items: center; justify-content: center; transition: opacity 0.2s, transform 0.2s; color: ${ACCENT_COLOR}; }
            #lr-reset:active, #lr-close:active { transform: scale(0.9); }
            #lr-reset:hover, #lr-close:hover { opacity: 0.7; }
            #lr-messages { position: relative; flex: 1; padding: 16px; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; gap: 12px; background: #f9f9f9; scrollbar-width: thin; scrollbar-color: rgba(0,0,0,0.12) transparent; overflow-anchor: none; }
            #lr-messages::-webkit-scrollbar { width: 4px; }
            #lr-messages::-webkit-scrollbar-track { background: transparent; }
            #lr-messages::-webkit-scrollbar-thumb { background-color: rgba(0,0,0,0.12); border-radius: 10px; }
            .lr-spacer { flex-grow: 1; min-height: 20px; pointer-events: none; }
            .lr-msg-row { display: flex; align-items: flex-end; gap: 8px; width: 100%; }
            .lr-msg-row.user { justify-content: flex-end; }
            .lr-msg-row.bot { justify-content: flex-start; }
            .lr-system-msg-row { display: flex; justify-content: center; width: 100%; margin: 4px 0; }
            .lr-system-msg { background: #fef3c7; color: #b45309; font-size: 11px; padding: 8px 12px; border-radius: 8px; text-align: center; max-width: 90%; line-height: 1.4; font-weight: 500; }
            .lr-msg { position: relative; max-width: 85%; padding: 10px 14px 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.6; word-wrap: break-word; animation: lr-msgIn 0.2s ease-out; display: block; width: fit-content; }
            .lr-msg.lr-has-table { max-width: 100%; width: 100%; }
            @keyframes lr-msgIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
            .lr-msg.user { background: ${PRIMARY_COLOR}; color: white; border-bottom-right-radius: 4px; }
            .lr-msg.bot { background: white; color: #1d1d1f; border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #eaeaea; }
            .lr-msg-text { word-wrap: break-word; }
            .lr-msg.bot ul { margin: 6px 0 6px 0; padding-left: 18px; }
            .lr-msg.bot li { margin: 0 0 4px 0; line-height: 1.5; }
            .lr-msg a { color: ${ACCENT_COLOR}; text-decoration: underline; word-break: break-word; }
            .lr-msg.lr-typing-bubble { padding: 12px 16px; display: flex; align-items: center; justify-content: center; width: fit-content; }
            .lr-luxury-thinking { font-size: 13px; color: #888; font-weight: 500; animation: lr-shimmer 1.5s infinite; }
            @keyframes lr-shimmer { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
            .lr-pad { display: inline-block; width: 40px; height: 1px; }
            .lr-pad.lr-has-src { width: 92px; }
            .lr-msg-footer { position: absolute; right: 12px; bottom: 7px; display: flex; align-items: center; gap: 8px; line-height: 1; margin: 0; width: auto; }
            .lr-timestamp { font-size: 10px; color: #aaa; flex-shrink: 0; }
            .lr-thumbs { display: flex; gap: 4px; opacity: 0; transition: opacity 0.2s; }
            .lr-msg:hover .lr-thumbs { opacity: 1; }
            .lr-thumb-btn { background: none; border: none; cursor: pointer; padding: 2px; color: #ccc; transition: color 0.2s; display: flex; align-items: center; }
            .lr-thumb-btn:hover { color: #666; }
            .lr-thumb-btn.active-up { color: #22c55e; }
            .lr-thumb-btn.active-down { color: #ef4444; }
            .lr-sources-details { position: relative; }
            .lr-sources-summary { background: none; border: none; padding: 0; margin: 0; color: #999; font-size: 11px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 4px; list-style: none; outline: none; user-select: none; }
            .lr-sources-summary:hover { color: #333; }
            .lr-sources-summary::-webkit-details-marker { display: none; }
            .lr-source-arrow { transition: transform 0.25s ease; width: 12px; height: 12px; }
            .lr-sources-details[open] .lr-source-arrow { transform: rotate(180deg); }
            .lr-sources-list { position: absolute; bottom: 100%; right: 0; margin-bottom: 6px; background: white; border: 1px solid #e5e5e5; padding: 8px 12px; border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); width: 240px; z-index: 99; animation: lr-msgIn 0.2s ease-out; }
            .lr-sources-list a, .lr-sources-list span { color: #777; font-size: 11px; text-decoration: none; display: block; margin-bottom: 6px; line-height: 1.4; word-wrap: break-word; white-space: normal; }
            .lr-sources-list a:last-child, .lr-sources-list span:last-child { margin-bottom: 0; }
            .lr-sources-list a:hover { color: #333; text-decoration: underline; }
            .lr-table-scroll { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 8px 0; border: 1px solid #dbe4f0; border-radius: 8px; }
            .lr-table { min-width: 100%; width: max-content; border-collapse: collapse; font-size: 12px; text-align: left; background: white; }
            .lr-table th { background: #eef4ff; color: ${PRIMARY_COLOR}; font-weight: 700; padding: 8px; border-bottom: 2px solid #dbe4f0; position: sticky; top: 0; }
            .lr-table td { padding: 8px; border-bottom: 1px solid #edf2f7; }
            .lr-table tr:nth-child(even) td { background: #f8fafd; }
            .lr-table tr:hover td { background: #f1f6ff; }
            .lr-table td:first-child { font-weight: 600; }
            .lr-table .lr-sticky-col { position: sticky; left: 0; background: white; border-right: 1px solid #dbe4f0; z-index: 2; }
            
            .lr-quick-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; padding-left: 32px; box-sizing: border-box; width: 100%; }
            .lr-action-chip { background: white; border: 1.5px solid ${ACCENT_COLOR}; color: ${PRIMARY_COLOR}; padding: 8px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.02); display: flex; align-items: center; gap: 8px; }
            .lr-action-chip svg { width: 14px; height: 14px; stroke-width: 2.5; stroke: currentColor; flex-shrink: 0; }
            .lr-action-chip:hover { background: rgba(192, 160, 96, 0.05); transform: translateY(-1.5px); box-shadow: 0 6px 16px rgba(192, 160, 96, 0.15); color: #000; }
            .lr-action-chip.lr-action-chip-primary { background: ${ACCENT_COLOR}; border-color: ${ACCENT_COLOR}; color: white; font-weight: 600; }
            
            #lr-legal-container { background: white; border-top: 1px solid #eee; padding: 16px; display: none; }
            .lr-legal-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #1d1d1f; }
            .lr-demo-warning { font-size: 11px; color: #b45309; background: #fef3c7; padding: 6px 10px; border-radius: 6px; margin-bottom: 12px; font-weight: 600; }
            .lr-legal-text { font-size: 13px; color: #555; margin-bottom: 16px; line-height: 1.5; }
            #lr-inline-agree-btn { background: ${ACCENT_COLOR}; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; width: 100%; margin-bottom: 10px; }
            .lr-terms-link { font-size: 11px; color: #86868b; text-align: center; display: block; }
            .lr-terms-link a { color: ${ACCENT_COLOR}; text-decoration: underline; }
            #lr-action-buttons { display: flex; gap: 8px; padding: 10px 12px 4px 12px; background: white; border-top: 1px solid #eee; }
            .lr-action-btn { flex: 1; text-align: center; padding: 8px; border-radius: 8px; font-size: 12px; font-weight: 700; text-decoration: none; transition: all 0.2s; cursor: pointer; border: none; }
            .lr-btn-enquiry { background: #f0f0f0; color: #1d1d1f; border: 1px solid #ddd; }
            .lr-btn-enquiry:hover { background: #e0e0e0; }
            .lr-btn-book { background: ${ACCENT_COLOR}; color: white; }
            .lr-btn-book:hover { filter: brightness(0.9); }
            #lr-input-area { padding: 8px 12px 10px 12px; background: white; display: flex; align-items: flex-end; gap: 8px; }
            #lr-input { flex: 1; padding: 10px 14px; border: 1px solid #ccc; border-radius: 20px; outline: none; font-size: 14px; transition: all 0.2s; background: #f9f9f9; font-family: inherit; line-height: 1.4; max-height: 120px; min-height: 40px; overflow-y: auto; resize: none; scrollbar-width: none; }
            #lr-input:focus { background: white; border-color: ${ACCENT_COLOR}; box-shadow: 0 0 0 3px rgba(192, 160, 96, 0.2); }
            #lr-send { background: ${ACCENT_COLOR}; color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-bottom: 2px; transition: transform 0.1s; }
            #lr-send:disabled { opacity: 0.4; cursor: not-allowed; }
            #lr-branding { text-align: center; font-size: 9px; color: #888; padding: 6px; background: #f9f9f9; border-top: 1px solid #eee; }
            #lr-confirm-modal { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 50; border-radius: 18px; }
            .lr-modal-content { background: white; padding: 24px; border-radius: 16px; width: 85%; max-width: 320px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            .lr-modal-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
            .lr-modal-text { font-size: 13px; color: #666; margin-bottom: 20px; }
            .lr-modal-actions { display: flex; gap: 10px; }
            .lr-modal-btn { flex: 1; padding: 10px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; }
            .lr-btn-cancel { background: #f0f0f0; color: #333; }
            .lr-btn-confirm { background: #ef4444; color: white; }

            /* STEP-BY-STEP CARD STYLES */
            .lr-step-card { background: white; border: 1px solid #eaeaea; border-radius: 12px; padding: 16px; margin-top: 4px; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05); position: relative; animation: lr-msgIn 0.3s ease-out; }
            .lr-step-title { font-weight: 700; font-size: 14px; margin-bottom: 10px; color: #1d1d1f; }
            .lr-step-input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 6px; font-size: 13px; font-family: inherit; outline: none; background: #fff; transition: border-color 0.2s; }
            .lr-step-input:focus { border-color: ${ACCENT_COLOR}; box-shadow: 0 0 0 2px rgba(192, 160, 96, 0.2); }
            .lr-step-input.error { border-color: #ef4444; background: #fef2f2; }
            .lr-error-text { color: #ef4444; font-size: 11px; margin-bottom: 10px; display: none; font-weight: 500; }
            .lr-error-text.show { display: block; animation: lr-msgIn 0.2s ease-out; }
            .lr-step-btn { width: 100%; padding: 10px; background: ${ACCENT_COLOR}; color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 13px; cursor: pointer; transition: filter 0.2s; margin-top: 4px; }
            .lr-step-btn:hover { filter: brightness(0.9); }
            .lr-step-btn:disabled { opacity: 0.5; cursor: not-allowed; }
            .lr-step-consent { display: flex; align-items: flex-start; gap: 8px; font-size: 11px; color: #666; margin-bottom: 12px; cursor: pointer; }
            .lr-step-consent input { margin-top: 2px; cursor: pointer; accent-color: ${ACCENT_COLOR}; }
            .lr-step-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
            .lr-step-chip { background: #f9f9f9; border: 1px solid #ddd; padding: 8px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; transition: all 0.2s; }
            .lr-step-chip:hover { border-color: ${ACCENT_COLOR}; background: white; }

            @media (max-width: 480px) {
                #lr-chat-window { width: calc(100vw - 24px); right: 12px; bottom: 75px; height: calc(100dvh - 100px); max-height: none; border-radius: 16px; }
                #lr-chat-btn { width: 46px; height: 46px; bottom: 16px; right: 16px; }
                .lr-msg { max-width: 88%; }
            }
        `;
        document.head.appendChild(style);

        const container = document.createElement('div');
        container.id = "lr-widget-container";
        container.innerHTML = `
            <button id="lr-chat-btn" aria-label="Open Chat">${iconChat}</button>
            <div id="lr-chat-window">
                <div id="lr-header">
                    <span id="lr-client-name-display">${CLIENT_NAME}</span>
                    <div class="lr-header-actions">
                        <button id="lr-reset" title="Start again">${iconRefresh}</button>
                        <button id="lr-close">${iconClose}</button>
                    </div>
                </div>
                <div id="lr-messages"></div>
                <div id="lr-confirm-modal">
                    <div class="lr-modal-content">
                        <div class="lr-modal-title">Start over?</div>
                        <div class="lr-modal-text">This will permanently clear your current chat history.</div>
                        <div class="lr-modal-actions">
                            <button id="lr-confirm-cancel" class="lr-modal-btn lr-btn-cancel">Cancel</button>
                            <button id="lr-confirm-yes" class="lr-modal-btn lr-btn-confirm">Yes, start over</button>
                        </div>
                    </div>
                </div>
                <div id="lr-legal-container">
                    <div class="lr-legal-title">Before we start</div>
                    <div class="lr-demo-warning" id="lr-demo-warning">Unofficial demo prepared by RanFie.</div>
                    <div class="lr-legal-text">This is an AI assistant, not medical advice. Confirm important info with the clinic. <strong>In an emergency, call 999.</strong></div>
                    <button id="lr-inline-agree-btn">I Agree</button>
                    <div class="lr-terms-link"><a href="${TERMS_URL}" target="_blank">Privacy Policy</a></div>
                </div>
                <div id="lr-action-buttons">
                    <button class="lr-action-btn lr-btn-enquiry" id="btn-leave-details">Request Callback</button>
                    <a href="${BOOKING_URL}" target="_blank" class="lr-action-btn lr-btn-book">Book Appointment</a>
                </div>
                <div id="lr-input-area">
                    <textarea id="lr-input" placeholder="Type your message..." rows="1"></textarea>
                    <button id="lr-send" aria-label="Send">${iconSend}</button>
                </div>
                <div id="lr-branding"><span style="color:#d97706; font-weight:600;">⚠️ Prices are a guide. Final price after consultation.</span><br>AI assistant. Emergency? 999.</div>
            </div>
        `;
        document.body.appendChild(container);

        const btn = document.getElementById('lr-chat-btn');
        const win = document.getElementById('lr-chat-window');
        const closeBtn = document.getElementById('lr-close');
        const resetBtn = document.getElementById('lr-reset');
        const input = document.getElementById('lr-input');
        const sendBtn = document.getElementById('lr-send');
        const messages = document.getElementById('lr-messages');
        const leaveDetailsBtn = document.getElementById('btn-leave-details');
        const legalContainer = document.getElementById('lr-legal-container');
        const actionButtons = document.getElementById('lr-action-buttons');
        const inputArea = document.getElementById('lr-input-area');
        const confirmModal = document.getElementById('lr-confirm-modal');
        const confirmCancel = document.getElementById('lr-confirm-cancel');
        const confirmYes = document.getElementById('lr-confirm-yes');

        let isOpen = false;
        if (IS_DEMO) document.getElementById('lr-demo-warning').style.display = "block";

        function checkLimits() {
            const today = new Date().toISOString().split('T')[0];
            let limitData = JSON.parse(localStorage.getItem("ranfie_limit_data") || "{}");
            if (limitData.date !== today) { limitData = { date: today, count: 0 }; localStorage.setItem("ranfie_limit_data", JSON.stringify(limitData)); }
            if (limitData.count >= MAX_DAILY_LIMIT || sessionCount >= MAX_SESSION_LIMIT) { input.disabled = true; sendBtn.disabled = true; input.placeholder = "Limit reached."; return false; }
            return true;
        }
        function incrementLimits() { sessionCount++; const today = new Date().toISOString().split('T')[0]; let limitData = JSON.parse(localStorage.getItem("ranfie_limit_data") || "{}"); limitData.count = (limitData.count || 0) + 1; localStorage.setItem("ranfie_limit_data", JSON.stringify(limitData)); checkLimits(); }
        function openChat() { isOpen = true; win.classList.add('lr-open'); btn.innerHTML = iconClose; btn.classList.add('lr-active'); const isAgreed = localStorage.getItem("ranfie_agreed") === "true"; const saved = sessionStorage.getItem("ranfie_chat_log"); if (isAgreed && !saved && !isTypingGreeting) { isTypingGreeting = true; simulateBotTyping(WELCOME_MESSAGE, true); } }
        function closeChat() { isOpen = false; win.classList.remove('lr-open'); btn.innerHTML = iconChat; btn.classList.remove('lr-active'); if (document.activeElement === input) input.blur(); }
        btn.onclick = (e) => { e.stopPropagation(); if (isOpen) { closeChat(); } else { openChat(); } };
        closeBtn.onclick = closeChat;
        document.addEventListener('click', (e) => { if (isOpen && !win.contains(e.target) && !btn.contains(e.target)) closeChat(); });
        win.addEventListener('click', (e) => e.stopPropagation()); 
        function resizeInput() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 120) + 'px'; }
        input.addEventListener('input', resizeInput);
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
        sendBtn.onclick = sendMessage;

        function getTime() { const d = new Date(); return d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0'); }
        
        function formatText(text) {
            if (!text) return "";
            let html = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const lines = html.split('\n');
            let inTable = false;
            let tableHtml = [];
            for (let i = 0; i < lines.length; i++) {
                let line = lines[i].trim();
                if (line.startsWith('|') && line.endsWith('|')) {
                    if (!inTable) {
                        inTable = true;
                        tableHtml.push('<div class="lr-table-scroll"><table class="lr-table">');
                        const headers = line.split('|').filter(c => c.trim() !== '').map(c => `<th>${c.trim()}</th>`).join('');
                        tableHtml.push(`<thead><tr>${headers}</tr></thead><tbody>`);
                    } else if (line.match(/^\|[\s\-\|]+\|$/)) {
                        lines[i] = ''; continue;
                    } else {
                        const cells = line.split('|').filter(c => c.trim() !== '').map((c, idx) => `<td class="${idx===0?'lr-sticky-col':''}">${c.trim()}</td>`).join('');
                        tableHtml.push(`<tr>${cells}</tr>`);
                    }
                    lines[i] = ''; 
                } else {
                    if (inTable) { tableHtml.push('</tbody></table></div>'); inTable = false; }
                }
            }
            if (inTable) tableHtml.push('</tbody></table></div>');
            let finalHtml = tableHtml.join('');
            html = lines.join('\n');
            html = html.replace(/([£$€]\s?[\d,]+(?:\.\d{2})?)/g, '<strong>$1</strong>');
            html = html.replace(/([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/g, '<strong>$1</strong>');
            html = html.replace(/\b(0\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4})\b/g, '<strong>$1</strong>');
            html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
            html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\*(.*?)\*/g, "<em>$1</em>");
            html = html.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>").replace(/\n/g, "<br>").replace(/(<br>){2,}/g, "<br>");
            html = html.replace(/<\/li><br><li>/g, "</li><li>").replace(/(?:<li>.*?<\/li>)+/gs, (m) => `<ul>${m}</ul>`);
            html = html.replace(/<br><\/ul>/g, "</ul>").replace(/<ul><br>/g, "<ul>").replace(/<li><\/li>/g, "");
            return finalHtml + html;
        }

        function buildBubbleInner(role, text, time, sources) {
            if (role === 'user') {
                const escapedText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                return `<div class="lr-msg-text">${escapedText}<span class="lr-pad"></span></div><div class="lr-msg-footer"><div class="lr-timestamp">${time}</div></div>`;
            }

            const hasSrc = role === 'bot' && sources && sources.length > 0;
            let html = `<div class="lr-msg-text">${formatText(text)}<span class="lr-pad ${hasSrc ? 'lr-has-src' : ''}"></span></div><div class="lr-msg-footer">`;
            if (role === 'bot') {
                html += `<div class="lr-thumbs">
                            <button class="lr-thumb-btn" onclick="submitFeedback(this, 1, '${text.replace(/'/g, "\\'")}')">${iconThumbUp}</button>
                            <button class="lr-thumb-btn" onclick="submitFeedback(this, -1, '${text.replace(/'/g, "\\'")}')">${iconThumbDown}</button>
                         </div>`;
            }
            if (hasSrc) {
                const formatted = sources.map(s => `<span>${s}</span>`).join("");
                html += `<details class="lr-sources-details"><summary class="lr-sources-summary">Sources<svg class="lr-source-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg></summary><div class="lr-sources-list">${formatted}</div></details>`;
            }
            return html + `<div class="lr-timestamp">${time}</div></div>`;
        }

        window.submitFeedback = async (btn, rating, botResponse) => {
            const parent = btn.parentElement;
            parent.querySelectorAll('.lr-thumb-btn').forEach(b => b.classList.remove('active-up', 'active-down'));
            btn.classList.add(rating === 1 ? 'active-up' : 'active-down');
            const lastUserMsg = chatLog.slice().reverse().find(m => m.role === 'user');
            const query = lastUserMsg ? lastUserMsg.content : "Unknown query";
            try {
                await fetch(FEEDBACK_URL, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Auth-Token': AUTH_TOKEN },
                    body: JSON.stringify({ query: query, response: botResponse, rating: rating })
                });
            } catch(e) { console.error("Feedback failed", e); }
        };

        function renderMessage(role, text, time, sources = []) {
            if (role === 'system') {
                const row = document.createElement('div'); row.className = 'lr-system-msg-row'; row.innerHTML = `<div class="lr-system-msg">${text}</div>`;
                const spacer = document.querySelector('.lr-spacer'); if (spacer) messages.insertBefore(row, spacer); else messages.appendChild(row); return row;
            }
            const row = document.createElement('div'); row.className = `lr-msg-row ${role === 'user' ? 'user' : 'bot'}`;
            const avatar = role === 'user' ? '' : botAvatar;
            row.innerHTML = avatar + `<div class="lr-msg ${role}">${buildBubbleInner(role, text, time, sources)}</div>`;
            if (role === 'bot' && text.includes('|')) { row.querySelector('.lr-msg').classList.add('lr-has-table'); }
            const spacer = document.querySelector('.lr-spacer'); if (spacer) messages.insertBefore(row, spacer); else messages.appendChild(row); return row;
        }

        function saveChat() { sessionStorage.setItem("ranfie_chat_log", JSON.stringify(chatLog)); }
        
        // --- STEP-BY-STEP CARD ENGINE ---
        function addBotMessage(text) {
            renderMessage('bot', text, getTime());
            chatLog.push({ role: 'assistant', content: text, time: getTime() }); saveChat();
        }

        function addUserMessage(text) {
            renderMessage('user', text, getTime());
            chatLog.push({ role: 'user', content: text, time: getTime() }); saveChat();
        }

        function startLeadFlow() {
            if (document.getElementById('lr-step-1')) return;
            leadData = {};
            addBotMessage("I can help with that. Let's get a few details so the reception team can call you back.");
            renderStep1();
        }

        function renderStep1() {
            const html = `
                <div class="lr-step-card" id="lr-step-1">
                    <div class="lr-step-title">What is your first name?</div>
                    <input type="text" id="lr-in-name" class="lr-step-input" placeholder="First Name">
                    <div id="lr-err-1" class="lr-error-text">Please enter a valid name.</div>
                    <button class="lr-step-btn" onclick="submitStep1()">Next</button>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;

            document.getElementById('lr-in-name').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') submitStep1();
            });
        }

        window.submitStep1 = () => {
            const name = document.getElementById('lr-in-name').value.trim();
            const inputEl = document.getElementById('lr-in-name');
            const errEl = document.getElementById('lr-err-1');
            
            if (name.length < 2) { 
                inputEl.classList.add('error');
                errEl.classList.add('show');
                return; 
            }
            
            document.getElementById('lr-step-1').closest('.lr-msg-row').remove();
            addUserMessage(name);
            leadData.name = name;
            addBotMessage(`Thanks ${name}. How can we reach you?`);
            renderStep2();
        };

        function renderStep2() {
            const html = `
                <div class="lr-step-card" id="lr-step-2">
                    <div class="lr-step-title">Phone or Email</div>
                    <input type="text" id="lr-in-contact" class="lr-step-input" placeholder="Phone or Email">
                    <div id="lr-err-2" class="lr-error-text">Please enter a valid phone number or email.</div>
                    <button class="lr-step-btn" onclick="submitStep2()">Next</button>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;

            document.getElementById('lr-in-contact').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') submitStep2();
            });
        }

        window.submitStep2 = () => {
            const contact = document.getElementById('lr-in-contact').value.trim();
            const inputEl = document.getElementById('lr-in-contact');
            const errEl = document.getElementById('lr-err-2');
            
            let isValid = false;
            
            // STRICTER VALIDATION (Email OR valid UK/International phone)
            if (contact.includes('@') && contact.includes('.')) {
                leadData.email = contact; leadData.phone = null; isValid = true;
            } else {
                // Remove spaces, dashes, parentheses
                const cleanNum = contact.replace(/[\s\-\(\)]/g, '');
                // Match UK mobile (07...), UK landline (01, 02, 03, 08...), or International (+...)
                const phoneRegex = /^(?:(?:\+44|0)7\d{9}|(?:\+44|0)[1238]\d{8,9}|\+\d{7,15})$/;
                
                if (phoneRegex.test(cleanNum)) {
                    leadData.phone = contact; leadData.email = null; isValid = true;
                }
            }

            if (!isValid) { 
                inputEl.classList.add('error');
                errEl.classList.add('show');
                return; 
            }
            
            document.getElementById('lr-step-2').closest('.lr-msg-row').remove();
            addUserMessage(contact);
            addBotMessage("Which treatment are you most interested in?");
            renderStep3();
        };

        function renderStep3() {
            const options = ["Invisalign", "Whitening", "Veneers", "Implants", "Check-up", "Other"];
            const chipsHtml = options.map(opt => `<div class="lr-step-chip" onclick="submitStep3('${opt}')">${opt}</div>`).join('');
            const html = `
                <div class="lr-step-card" id="lr-step-3">
                    <div class="lr-step-title">Select Treatment</div>
                    <div class="lr-step-chips">${chipsHtml}</div>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;
        }

        window.submitStep3 = (treatment) => {
            document.getElementById('lr-step-3').closest('.lr-msg-row').remove();
            addUserMessage(treatment);
            leadData.treatment = treatment;
            addBotMessage("When is the best time for the clinic to call you?");
            renderStep4();
        };

        function renderStep4() {
            const options = ["Morning", "Afternoon", "Evening", "Any time"];
            const chipsHtml = options.map(opt => `<div class="lr-step-chip" onclick="submitStep4('${opt}')">${opt}</div>`).join('');
            const html = `
                <div class="lr-step-card" id="lr-step-4">
                    <div class="lr-step-title">Select Time</div>
                    <div class="lr-step-chips">${chipsHtml}</div>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;
        }

        window.submitStep4 = (time) => {
            document.getElementById('lr-step-4').closest('.lr-msg-row').remove();
            addUserMessage(time);
            leadData.time = time;
            addBotMessage("Are you a new or existing patient?");
            renderStep5();
        };

        function renderStep5() {
            const options = ["New Patient", "Existing Patient"];
            const chipsHtml = options.map(opt => `<div class="lr-step-chip" onclick="submitStep5('${opt}')">${opt}</div>`).join('');
            const html = `
                <div class="lr-step-card" id="lr-step-5">
                    <div class="lr-step-title">Patient Type</div>
                    <div class="lr-step-chips">${chipsHtml}</div>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;
        }

        window.submitStep5 = (patient) => {
            document.getElementById('lr-step-5').closest('.lr-msg-row').remove();
            addUserMessage(patient);
            leadData.patient = patient;
            addBotMessage("Almost done! Please confirm you agree to be contacted.");
            renderStep6();
        };

        function renderStep6() {
            const html = `
                <div class="lr-step-card" id="lr-step-6">
                    <div class="lr-step-title">GDPR Consent</div>
                    <label class="lr-step-consent">
                        <input type="checkbox" id="lr-in-consent">
                        <span>I agree to be contacted by ${CLIENT_NAME} about my enquiry.</span>
                    </label>
                    <button class="lr-step-btn" id="lr-btn-submit-lead" onclick="submitStep6()" disabled>Submit Request</button>
                </div>
            `;
            const row = document.createElement('div'); row.className = 'lr-msg-row bot';
            row.innerHTML = botAvatar + `<div class="lr-msg bot" style="max-width: 100%; width: 100%; padding: 0; background: transparent; border: none; box-shadow: none;">${html}</div>`;
            messages.insertBefore(row, document.querySelector('.lr-spacer'));
            messages.scrollTop = messages.scrollHeight;

            document.getElementById('lr-in-consent').addEventListener('change', (e) => {
                document.getElementById('lr-btn-submit-lead').disabled = !e.target.checked;
            });
        }

        window.submitStep6 = async () => {
            const btn = document.getElementById('lr-btn-submit-lead');
            btn.innerText = "Sending...";
            btn.disabled = true;

            try {
                const res = await fetch(LEAD_URL, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Auth-Token': AUTH_TOKEN },
                    body: JSON.stringify({ 
                        name: leadData.name, phone: leadData.phone, email: leadData.email, 
                        treatment: leadData.treatment, preferred_time: leadData.time,
                        patient_type: leadData.patient, consent_given: true 
                    })
                });
                
                if (res.ok) {
                    document.getElementById('lr-step-6').closest('.lr-msg-row').remove();
                    addBotMessage(`Thank you, ${leadData.name}. The clinic will contact you within 24 hours.`);
                    sessionStorage.setItem("lead_captured", "true");
                    sessionStorage.setItem("lead_offered", "true");
                } else {
                    btn.innerText = "Try Again"; btn.disabled = false;
                }
            } catch (e) {
                btn.innerText = "Try Again"; btn.disabled = false;
            }
        };
        // --- END STEP-BY-STEP CARD ENGINE ---

        const svgIcons = {
            "book appointment": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>`,
            "treatment pricing": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>`,
            "emergency dentist": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M19 8h-2v3h-3v2h3v3h2v-3h3v-2h-3V8z"></path><path d="M12 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10"></path></svg>`,
            "opening hours": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
            "default": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>`
        };

        function simulateBotTyping(text, showQuickActions = false) {
            const timeNow = getTime(); chatLog.push({ role: 'assistant', content: text, time: timeNow }); saveChat();
            conversationHistory = chatLog.filter(m => m.role !== 'system').map(msg => ({ role: msg.role, content: msg.content }));
            const botRow = document.createElement('div'); botRow.className = 'lr-msg-row bot';
            const botDiv = document.createElement('div'); botDiv.className = 'lr-msg bot lr-typing-bubble'; botDiv.innerHTML = '<div class="lr-luxury-thinking">Thinking...</div>';
            botRow.innerHTML = botAvatar; botRow.appendChild(botDiv);
            const spacer = document.querySelector('.lr-spacer'); if (spacer) messages.insertBefore(botRow, spacer); else messages.appendChild(botRow);
            setTimeout(() => { messages.scrollTop = messages.scrollHeight; }, 20);
            setTimeout(() => {
                botDiv.classList.remove('lr-typing-bubble'); botDiv.innerHTML = buildBubbleInner('bot', text, timeNow, []);
                if (showQuickActions && QUICK_ACTIONS.length > 0) {
                    const chipsRow = document.createElement('div'); chipsRow.className = 'lr-quick-actions'; chipsRow.id = 'lr-initial-chips';
                    QUICK_ACTIONS.forEach((action, index) => {
                        const chip = document.createElement('button'); chip.className = 'lr-action-chip';
                        if (index === 0) chip.classList.add('lr-action-chip-primary');
                        const lowerAction = action.toLowerCase(); const iconSvg = svgIcons[lowerAction] || svgIcons["default"];
                        chip.innerHTML = `${iconSvg} <span>${action}</span>`;
                        chip.onclick = () => {
                            const existingChips = document.getElementById('lr-initial-chips'); if (existingChips) existingChips.remove();
                            let instantResponse = null;
                            if (INSTANT_ANSWERS && Object.keys(INSTANT_ANSWERS).length > 0) {
                                for (const key in INSTANT_ANSWERS) { if (INSTANT_ANSWERS[key].keywords.some(kw => lowerAction.includes(kw))) { instantResponse = INSTANT_ANSWERS[key].response; break; } }
                            } 
                            if (!instantResponse) { input.value = action; sendMessage(); }
                            else {
                                const t = getTime(); renderMessage('user', action, t); chatLog.push({ role: 'user', content: action, time: t });
                                const bt = getTime(); renderMessage('bot', instantResponse, bt); chatLog.push({ role: 'assistant', content: instantResponse, time: bt });
                                saveChat(); messages.scrollTop = messages.scrollHeight; incrementLimits();
                            }
                        };
                        chipsRow.appendChild(chip);
                    });
                    const spacer = document.querySelector('.lr-spacer'); if (spacer) messages.insertBefore(chipsRow, spacer); else messages.appendChild(chipsRow);
                }
            }, 300); 
        }

        function loadChat() {
            messages.innerHTML = ""; const isAgreed = localStorage.getItem("ranfie_agreed") === "true"; const saved = sessionStorage.getItem("ranfie_chat_log");
            if (!isAgreed) {
                input.disabled = true; sendBtn.disabled = true; legalContainer.style.display = "block"; actionButtons.style.display = "none"; inputArea.style.display = "none";
                const spacer = document.createElement('div'); spacer.className = 'lr-spacer'; messages.appendChild(spacer);
            } else {
                legalContainer.style.display = "none"; actionButtons.style.display = "flex"; inputArea.style.display = "flex"; input.disabled = false; sendBtn.disabled = false;
                if (saved) {
                    chatLog = JSON.parse(saved); conversationHistory = chatLog.filter(m => m.role !== 'system').map(msg => ({ role: msg.role, content: msg.content }));
                    sessionCount = chatLog.filter(m => m.role === 'user').length;
                    userMessageCount = sessionCount;
                    const spacer = document.createElement('div'); spacer.className = 'lr-spacer'; messages.appendChild(spacer);
                    chatLog.forEach(msg => renderMessage(msg.role, msg.content, msg.time, msg.sources));
                    messages.scrollTop = messages.scrollHeight; checkLimits();
                } else {
                    const timeNow = getTime(); const dateStr = new Date().toLocaleDateString('en-GB'); const systemMsg = `🔒 You agreed to the Terms of Service on ${dateStr}.`;
                    const spacer = document.createElement('div'); spacer.className = 'lr-spacer'; messages.appendChild(spacer);
                    chatLog = []; chatLog.push({ role: 'system', content: systemMsg, time: timeNow }); renderMessage('system', systemMsg, timeNow); checkLimits();
                }
            }
        }
        document.getElementById('lr-inline-agree-btn').onclick = () => {
            localStorage.setItem("ranfie_agreed", "true"); legalContainer.style.display = "none"; actionButtons.style.display = "flex"; inputArea.style.display = "flex"; input.disabled = false; sendBtn.disabled = false;
            const timeNow = getTime(); const dateStr = new Date().toLocaleDateString('en-GB'); const systemMsg = `🔒 You agreed to the Terms of Service on ${dateStr}.`;
            messages.innerHTML = ""; const spacer = document.createElement('div'); spacer.className = 'lr-spacer'; messages.appendChild(spacer);
            chatLog = []; chatLog.push({ role: 'system', content: systemMsg, time: timeNow }); renderMessage('system', systemMsg, timeNow);
            isTypingGreeting = true; simulateBotTyping(WELCOME_MESSAGE, true); checkLimits();
        };
        loadChat();
        resetBtn.onclick = () => { confirmModal.style.display = 'flex'; };
        confirmCancel.onclick = () => { confirmModal.style.display = 'none'; };
        confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) confirmModal.style.display = 'none'; });
        confirmYes.onclick = () => {
            confirmModal.style.display = 'none'; sessionStorage.removeItem("ranfie_chat_log"); chatLog = []; conversationHistory = []; sessionCount = 0; userMessageCount = 0; isTypingGreeting = false; 
            loadChat(); isTypingGreeting = true; simulateBotTyping(WELCOME_MESSAGE, true); input.value = ""; input.style.height = 'auto'; 
        };
        
        leaveDetailsBtn.onclick = startLeadFlow;

        async function sendMessage() {
            if (!checkLimits()) return; const text = input.value.trim(); if (!text) return;
            
            const isEmergency = emergencyKeywords.some(kw => text.toLowerCase().includes(kw));
            
            incrementLimits(); userMessageCount++;
            const timeNow = getTime();
            const existingChips = document.getElementById('lr-initial-chips'); if (existingChips) existingChips.remove();
            let oldSpacer = document.querySelector('.lr-spacer'); if (oldSpacer) oldSpacer.remove();
            
            const userRow = renderMessage('user', text, timeNow); chatLog.push({ role: 'user', content: text, time: timeNow }); saveChat();
            input.value = ""; input.style.height = '40px'; input.disabled = true; sendBtn.disabled = true;
            const container = document.getElementById('lr-messages');
            setTimeout(() => { container.scrollTop = userRow.offsetTop - (container.clientHeight * 0.60); }, 50);
            
            const botRow = document.createElement('div'); botRow.className = 'lr-msg-row bot';
            const botDiv = document.createElement('div'); botDiv.className = 'lr-msg bot lr-typing-bubble'; botDiv.innerHTML = '<div class="lr-luxury-thinking">Thinking...</div>';
            botRow.innerHTML = botAvatar; botRow.appendChild(botDiv);
            let spacer = document.createElement('div'); spacer.className = 'lr-spacer'; messages.appendChild(botRow); messages.appendChild(spacer);

            let accumulatedText = "";
            let currentSources = [];
            let isFirstChunk = true;

            try {
                const res = await fetch(STREAM_URL, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Auth-Token': AUTH_TOKEN },
                    body: JSON.stringify({ message: text, history: conversationHistory })
                });

                if (!res.ok) throw new Error("HTTP error");

                const reader = res.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split("\n\n");
                    buffer = parts.pop(); 

                    for (const part of parts) {
                        if (!part.startsWith("data: ")) continue;
                        const dataString = part.slice(6).trim();
                        if (!dataString) continue;
                        
                        const event = JSON.parse(dataString);
                        if (event.type === "sources") {
                            currentSources = event.data;
                        } else if (event.type === "token") {
                            if (isFirstChunk) {
                                botDiv.classList.remove('lr-typing-bubble');
                                botDiv.innerHTML = '<div class="lr-msg-text" style="width: 100%;"><span class="lr-stream-text" style="white-space: pre-wrap; display: block; word-break: break-word;"></span></div>';
                                isFirstChunk = false;
                            }
                            accumulatedText += event.data;
                            const streamNode = botDiv.querySelector('.lr-stream-text');
                            if (streamNode) streamNode.textContent = accumulatedText;
                            messages.scrollTop = messages.scrollHeight;
                        }
                    }
                }

                const timeBot = getTime();
                const finalText = accumulatedText.trim() === "" ? "I don't have that information. Please contact the clinic." : accumulatedText;
                
                chatLog.push({ role: 'assistant', content: finalText, time: timeBot, sources: currentSources }); saveChat();
                conversationHistory = chatLog.filter(m => m.role !== 'system').map(msg => ({ role: msg.role, content: msg.content }));
                
                botDiv.innerHTML = buildBubbleInner('bot', finalText, timeBot, currentSources);
                if (finalText.includes('|')) { botDiv.classList.add('lr-has-table'); }

                // SMART LEAD TRIGGER
                const leadCaptured = sessionStorage.getItem("lead_captured") === "true";
                if (!isEmergency && (finalText.includes("I don't have that information") || userMessageCount >= 3) && !sessionStorage.getItem("lead_offered") && !leadCaptured) {
                    sessionStorage.setItem("lead_offered", "true");
                    setTimeout(() => {
                        const promptRow = document.createElement('div'); promptRow.className = 'lr-msg-row bot';
                        promptRow.innerHTML = `<div class="lr-msg bot" style="background:#f0f8ff; border-color:#b0c4de; color:#333;">Would you like to leave your name and number so the reception team can call you back?</div>`;
                        messages.insertBefore(promptRow, document.querySelector('.lr-spacer'));
                        messages.scrollTop = messages.scrollHeight;
                        setTimeout(() => { startLeadFlow(); }, 1000);
                    }, 800);
                }

                input.disabled = false; sendBtn.disabled = false; checkLimits(); messages.scrollTop = messages.scrollHeight;

            } catch (error) {
                console.error(error);
                botDiv.innerHTML = `<div class="lr-msg-text" style="color:red;">Sorry, I am having trouble connecting right now.</div>`;
                input.disabled = false; sendBtn.disabled = false; checkLimits();
            }
        }
    }
})();