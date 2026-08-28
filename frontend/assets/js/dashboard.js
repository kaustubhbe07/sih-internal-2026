const API_BASE_URL = "http://127.0.0.1:8001";

// Ensure auth headers are added to all fetch requests
function getAuthHeaders() {
    const token = localStorage.getItem('certify_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

// Global state for registry
window.allCredentials = [];
let currentPage = 1;
const itemsPerPage = 10;
let currentSearch = '';

// 1. Fetch Overview (Stats and Activity Feed)
async function fetchOverview() {
    try {
        const response = await fetch(`${API_BASE_URL}/credentials/mine`, {
            method: 'GET',
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('certify_token');
            window.location.href = "login.html";
            return;
        }

        const data = await response.json();
        
        // Sort data by newest first (descending)
        const sortedData = [...data].sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });
        
        window.allCredentials = sortedData;
        
        // Calculate Stats
        const totalIssued = data.length;
        const revoked = data.filter(c => c.revoked).length;
        const active = totalIssued - revoked;

        // Update Stats DOM
        document.getElementById('stats-total').textContent = totalIssued.toLocaleString();
        document.getElementById('stats-active').textContent = active.toLocaleString();
        document.getElementById('stats-revoked').textContent = revoked.toLocaleString();

        // Render Activity Feed
        const feedContainer = document.getElementById('activity-list');
        if (feedContainer) {
            feedContainer.innerHTML = ''; // Clear loading text
        }

        if (data.length === 0) {
            if (feedContainer) feedContainer.innerHTML = '<div style="text-align: center; color: var(--gray-500); padding: 20px;">No credentials issued yet.</div>';
            renderRegistryTable();
            return;
        }

        // Take top 5 for recent activity
        const recentActivity = window.allCredentials.slice(0, 5);

        recentActivity.forEach(cred => {
            // Determine styling based on revocation status
            const iconBg = cred.revoked ? 'bg-red-500' : 'bg-blue-500';
            const iconSvg = cred.revoked 
                ? `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`
                : `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>`;
            
            const badgeClass = cred.revoked ? 'revoked' : 'success';
            const badgeText = cred.revoked ? 'REVOKED' : 'SUCCESS';
            
            const feedTitle = cred.revoked
                ? `Revoked ${cred.degree} of ${cred.student_name}`
                : `Issued ${cred.degree} to ${cred.student_name}`;
            
            // Format time ago
            const timeDiff = Math.floor((new Date() - new Date(cred.created_at)) / 1000);
            let timeAgo = "Just now";
            if (timeDiff > 3600) {
                timeAgo = Math.floor(timeDiff / 3600) + " hrs ago";
            } else if (timeDiff > 60) {
                timeAgo = Math.floor(timeDiff / 60) + " mins ago";
            }

            // Short Hash
            const shortHash = cred.record_hash.substring(0, 4) + '...' + cred.record_hash.substring(cred.record_hash.length - 4);

            const itemHtml = `
                <div class="feed-item">
                    <div class="feed-icon ${iconBg}">${iconSvg}</div>
                    <div class="feed-details">
                        <div class="feed-title">${feedTitle}</div>
                        <div class="feed-hash" style="cursor: pointer;" onclick="copyHash(event, '${cred.record_hash}')" title="Click to copy full hash">Hash: 0x${shortHash} <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></div>
                    </div>
                    <div class="feed-meta">
                        <div class="feed-time">${timeAgo}</div>
                        <div class="feed-badge ${badgeClass}">${badgeText}</div>
                    </div>
                </div>
            `;
            if (feedContainer) feedContainer.insertAdjacentHTML('beforeend', itemHtml);
        });

        renderRegistryTable();

    } catch (err) {
        console.error("Failed to fetch overview", err);
        const feedContainer = document.getElementById('activity-list');
        if (feedContainer) feedContainer.innerHTML = '<div style="text-align: center; color: red; padding: 20px;">Failed to load data. Make sure backend is running.</div>';
    }
}

// 2. Issue Credential
async function issueCredential(e) {
    e.preventDefault();
    
    const name = document.getElementById('issueName').value;
    const roll = document.getElementById('issueRoll').value;
    const degree = document.getElementById('issueDegree').value;
    const issueDate = document.getElementById('issueDate').value;

    // Collect custom fields
    const customFieldsContainer = document.getElementById('dynamic-fields-container');
    const fieldGroups = customFieldsContainer.querySelectorAll('.custom-field-group');
    const customFields = {};

    fieldGroups.forEach(group => {
        const select = group.querySelector('.field-key-select');
        const customInput = group.querySelector('.field-key-input');
        const valueInput = group.querySelector('.field-value-input');
        
        if (select && valueInput) {
            let key = select.value;
            if (key === "Other (Custom)" && customInput) {
                key = customInput.value.trim();
            }
            const val = valueInput.value.trim();
            
            if (key && val) {
                customFields[key] = val;
            }
        }
    });

    // We can extract CGPA if it was added as a custom field (or send as normal)
    let cgpa = null;
    if (customFields["CGPA"]) {
        cgpa = customFields["CGPA"];
        delete customFields["CGPA"];
    }

    const payload = {
        student_name: name,
        roll_no: roll,
        degree: degree,
        cgpa: cgpa,
        issue_date: issueDate,
        custom_fields: Object.keys(customFields).length > 0 ? customFields : null
    };

    try {
        const response = await fetch(`${API_BASE_URL}/credentials`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        if (response.ok) {
            alert(`Credential Issued Successfully!\nID: ${data.id}`);
            document.getElementById('issueForm').reset();
            
            customFieldsContainer.innerHTML = '';
            // Refresh Overview
            fetchOverview();
        } else {
            alert(`Error: ${data.detail || JSON.stringify(data)}`);
        }
    } catch (err) {
        console.error(err);
        alert("Network Error");
    }
}

// 3. Upload CSV Bulk
async function uploadCSV(e) {
    e.preventDefault();
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const token = localStorage.getItem('certify_token');
        const response = await fetch(`${API_BASE_URL}/credentials/bulk`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
                // Note: Do NOT set Content-Type for FormData, the browser will set it to multipart/form-data with boundary
            },
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            alert(`Batch Upload Complete!\nTotal Issued: ${data.total_issued}`);
            document.getElementById('bulkForm').reset();
            fetchOverview(); // refresh
        } else {
            alert(`Upload Failed:\n${JSON.stringify(data.detail)}`);
        }
    } catch (err) {
        console.error(err);
        alert("Network Error");
    }
}

// 4. Revoke Credential
async function revokeCredential(e) {
    e.preventDefault();
    const credId = document.getElementById('revokeId').value.trim();

    if (!credId) return;

    const reason = prompt("Enter a reason for revocation:", "Administrative Revocation");
    if (reason === null) return; // User cancelled

    const payload = {
        credential_id: credId,
        reason: reason
    };

    try {
        const response = await fetch(`${API_BASE_URL}/revocations`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully revoked credential:\n${data.credential_id}`);
            document.getElementById('revokeForm').reset();
            fetchOverview(); // refresh
        } else {
            alert(`Error: ${data.detail || JSON.stringify(data)}`);
        }
    } catch (err) {
        console.error(err);
        alert("Network Error");
    }
}

// 5. Registry Table Logic
function renderRegistryTable() {
    const tbody = document.getElementById('registry-table-body');
    if (!tbody) return;

    // Filter data
    let filtered = window.allCredentials;
    if (currentSearch) {
        const s = currentSearch.toLowerCase();
        filtered = filtered.filter(c => 
            (c.student_name && c.student_name.toLowerCase().includes(s)) ||
            (c.roll_no && c.roll_no.toLowerCase().includes(s)) ||
            (c.degree && c.degree.toLowerCase().includes(s)) ||
            (c.record_hash && c.record_hash.toLowerCase().includes(s))
        );
    }

    const totalRecords = filtered.length;
    const totalPages = Math.ceil(totalRecords / itemsPerPage) || 1;
    if (currentPage > totalPages) currentPage = totalPages;

    const startIdx = (currentPage - 1) * itemsPerPage;
    const endIdx = startIdx + itemsPerPage;
    const pageData = filtered.slice(startIdx, endIdx);

    // Update text
    document.getElementById('registry-count-text').textContent = `Showing ${totalRecords > 0 ? startIdx + 1 : 0}-${Math.min(endIdx, totalRecords)} of ${totalRecords} records`;

    // Render Rows
    tbody.innerHTML = '';
    pageData.forEach(cred => {
        const shortHash = cred.record_hash.substring(0, 4) + '...' + cred.record_hash.substring(cred.record_hash.length - 4);
        const statusHtml = cred.revoked 
            ? `<span class="status-revoked">Revoked</span>`
            : `<span class="status-active">Active</span>`;
        
        // Format Date (e.g. Oct 14, 2023)
        const dateObj = new Date(cred.issue_date);
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

        const revokeBtnHtml = cred.revoked 
            ? `<button title="Already Revoked" disabled style="color: #cbd5e1; cursor: not-allowed;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg></button>`
            : `<button title="Revoke Credential" onclick="promptRevokeFromTable(event, '${cred.id}')" style="color: #dc2626;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg></button>`;

        const tr = document.createElement('tr');

        tr.innerHTML = `
            <td>${cred.roll_no}</td>
            <td style="font-weight: 500;">${cred.student_name}</td>
            <td style="color: var(--text-muted);">${dateStr}</td>
            <td><span class="hash-badge" style="cursor: pointer;" onclick="copyHash(event, '${cred.record_hash}')" title="Click to copy full hash">0x${shortHash} <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:10px;vertical-align:middle;margin-left:4px;"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></span></td>
            <td>${statusHtml}</td>
            <td class="actions" style="text-align: right;">
                <button title="View JSON" onclick="openRegistryModal('${cred.id}')">{ }</button>
                <button title="Download Certificate" onclick="downloadCert('${cred.id}')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg></button>
                <button title="View QR" onclick="downloadQR('${cred.id}')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg></button>
                ${revokeBtnHtml}
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Render Pagination
    const pageContainer = document.getElementById('registry-pagination');
    if (pageContainer) {
        pageContainer.innerHTML = '';
        for (let i = 1; i <= totalPages; i++) {
            // Very simple pagination display (no ellipses logic for now)
            if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                const span = document.createElement('span');
                span.className = `page-num ${i === currentPage ? 'active' : ''}`;
                span.textContent = i;
                span.onclick = () => { currentPage = i; renderRegistryTable(); };
                pageContainer.appendChild(span);
            } else if (i === 2 && currentPage > 3) {
                const dot = document.createElement('span'); dot.textContent = '...'; pageContainer.appendChild(dot);
            } else if (i === totalPages - 1 && currentPage < totalPages - 2) {
                const dot = document.createElement('span'); dot.textContent = '...'; pageContainer.appendChild(dot);
            }
        }
    }
}

function changePage(dir) {
    currentPage += dir;
    if (currentPage < 1) currentPage = 1;
    renderRegistryTable();
}

function filterRegistry() {
    currentSearch = document.getElementById('registrySearch').value;
    currentPage = 1;
    renderRegistryTable();
}

// 6. Modal and Downloads
function openRegistryModal(credId) {
    const cred = window.allCredentials.find(c => c.id === credId);
    if (!cred) return;

    // Construct the payload as it would appear on chain
    const payloadObj = {
        institution_id: cred.institution_id,
        student_name: cred.student_name,
        roll_no: cred.roll_no,
        degree: cred.degree,
        cgpa: cred.cgpa,
        issue_date: cred.issue_date,
        custom_fields: cred.custom_fields,
        prev_hash: cred.prev_hash
    };

    document.getElementById('modalJson').textContent = JSON.stringify(payloadObj, null, 2);
    document.getElementById('modalSignature').textContent = cred.signature || "Signature not available";
    document.getElementById('jsonModal').style.display = 'flex';
}

function closeRegistryModal() {
    document.getElementById('jsonModal').style.display = 'none';
}

function downloadCert(credId) {
    window.open(`${API_BASE_URL}/credentials/${credId}/certificate`, '_blank');
}

function downloadQR(credId) {
    window.open(`${API_BASE_URL}/credentials/${credId}/qr`, '_blank');
}

async function promptRevokeFromTable(e, credId) {
    e.stopPropagation();
    
    const reason = prompt("Are you sure you want to revoke this credential?\n\nEnter a reason for revocation:", "Administrative Revocation");
    if (reason === null) return; // User cancelled

    const payload = {
        credential_id: credId,
        reason: reason
    };

    try {
        const response = await fetch(`${API_BASE_URL}/revocations`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully revoked credential!`);
            fetchOverview(); // refresh table and stats
        } else {
            alert(`Error: ${data.detail || JSON.stringify(data)}`);
        }
    } catch (err) {
        console.error(err);
        alert("Network Error");
    }
}

async function copyHash(e, hashStr) {
    e.stopPropagation(); // Prevent the row click event from firing (which opens JSON modal)
    try {
        const fullHash = "0x" + hashStr;
        await navigator.clipboard.writeText(fullHash);
        
        // Show a brief, non-intrusive visual feedback on the target element
        const target = e.currentTarget;
        const originalText = target.innerHTML;
        target.innerHTML = `<span style="color: #16a34a;">Copied!</span>`;
        setTimeout(() => {
            target.innerHTML = originalText;
        }, 1000);
    } catch (err) {
        console.error('Failed to copy: ', err);
        alert("Failed to copy hash to clipboard.");
    }
}

// Execute on load
window.addEventListener('DOMContentLoaded', () => {
    // Only run if we're on the dashboard and logged in (token exists)
    if (localStorage.getItem('certify_token')) {
        fetchOverview();
    }

    // --- CERTIFICATE PREVIEW LOGIC ---
    
    // Live Data Binding
    const nameInput = document.getElementById('issueName');
    const degreeInput = document.getElementById('issueDegree');
    const dateInput = document.getElementById('issueDate');
    
    if (nameInput) {
        nameInput.addEventListener('input', (e) => {
            document.getElementById('prev-name').textContent = e.target.value || 'Student Name';
        });
    }
    if (degreeInput) {
        degreeInput.addEventListener('input', (e) => {
            document.getElementById('prev-degree').textContent = e.target.value || 'Degree Program';
        });
    }
    if (dateInput) {
        dateInput.addEventListener('input', (e) => {
            if (e.target.value) {

                const d = new Date(e.target.value);
                document.getElementById('prev-date').textContent = "Issued: " + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            } else {
                document.getElementById('prev-date').textContent = '';
            }
        });
    }

    const rollInput = document.getElementById('issueRoll');
    if (rollInput) {
        rollInput.addEventListener('input', (e) => {
            document.getElementById('prev-roll').textContent = e.target.value || 'N/A';
        });
    }

    // Dynamic Fields Binding
    const customContainer = document.getElementById('dynamic-fields-container');
    function updateCustomFieldsPreview() {
        const previewContainer = document.getElementById('prev-custom-fields');
        if (!previewContainer) return;
        
        const fieldGroups = document.querySelectorAll('.custom-field-group');
        let html = '';
        fieldGroups.forEach(group => {
            const select = group.querySelector('.field-key-select');
            const customInput = group.querySelector('.field-key-input');
            const valueInput = group.querySelector('.field-value-input');
            
            let key = select ? select.value : '';
            if (key === "Other (Custom)" && customInput) {
                key = customInput.value.trim();
            }
            const val = valueInput ? valueInput.value.trim() : '';
            
            if (key && val) {
                html += `<div style="font-size: 0.75rem; color: #475569;"><strong style="color:#0f172a;">${key}:</strong> ${val}</div>`;
            }
        });
        previewContainer.innerHTML = html;
    }

    if (customContainer) {
        customContainer.addEventListener('input', updateCustomFieldsPreview);
        customContainer.addEventListener('change', updateCustomFieldsPreview);
        const observer = new MutationObserver(updateCustomFieldsPreview);
        observer.observe(customContainer, { childList: true, subtree: true });
    }
    
    // 3D Hover Effect
    const certContainer = document.getElementById('cert-preview-container');
    const certCard = document.getElementById('cert-card');
    
    if (certContainer && certCard) {
        certContainer.addEventListener('mousemove', (e) => {
            const rect = certContainer.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // Calculate rotation (max 12 degrees)
            const rotateX = ((y - centerY) / centerY) * -12;
            const rotateY = ((x - centerX) / centerX) * 12;
            
            certCard.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });
        
        certContainer.addEventListener('mouseleave', () => {
            certCard.style.transform = `rotateX(0deg) rotateY(0deg)`;
        });
    }
});

async function verifyCredential() {
    const credId = document.getElementById('verifier-id-input').value.trim();
    if (!credId) {
        alert("Please enter a Credential ID");
        return;
    }

    try {
        const response = await fetch(`http://127.0.0.1:8001/verify/${credId}`);
        if (!response.ok) {
            if (response.status === 404) {
                alert("Credential not found.");
            } else {
                alert("Error verifying credential.");
            }
            return;
        }

        const data = await response.json();
        
        // Navigate to result view
        window.location.hash = '#verifier-result';

        // Update DOM
        const title = document.getElementById('vr-status-title');
        const desc = document.getElementById('vr-status-desc');
        const card = document.getElementById('vr-details-card');
        const banner = document.getElementById('vr-banner');
        const iconSuccess = document.getElementById('vr-icon-success');
        const iconFail = document.getElementById('vr-icon-fail');

        if (data.status === "VALID") {
            title.textContent = "CREDENTIAL VERIFIED";
            banner.className = "result-banner result-banner-valid";
            iconSuccess.style.display = "block";
            iconFail.style.display = "none";
            desc.textContent = "This document matches the blockchain ledger and was officially signed by " + (data.credential?.institution_name || "the institution") + ".";
        } else if (data.status === "REVOKED") {
            title.textContent = "CREDENTIAL REVOKED";
            banner.className = "result-banner result-banner-invalid";
            iconSuccess.style.display = "none";
            iconFail.style.display = "block";
            const revDate = data.revocation ? new Date(data.revocation.revoked_at).toLocaleDateString() : "an unknown date";
            const reason = data.revocation ? data.revocation.reason : "";
            desc.textContent = `This credential was revoked on ${revDate}. Reason: ${reason}`;
        } else {
            title.textContent = "INVALID CREDENTIAL";
            banner.className = "result-banner result-banner-invalid";
            iconSuccess.style.display = "none";
            iconFail.style.display = "block";
            desc.textContent = "This document could not be cryptographically verified.";
        }

        if (data.credential) {
            card.style.display = 'block';
            document.getElementById('vr-student-name').textContent = data.credential.student_name;
            document.getElementById('vr-initials').textContent = data.credential.student_name.substring(0, 2).toUpperCase();
            document.getElementById('vr-roll').textContent = data.credential.roll_no;
            document.getElementById('vr-degree').textContent = data.credential.degree;
            document.getElementById('vr-cgpa').textContent = data.credential.cgpa || 'N/A';
            document.getElementById('vr-date').textContent = new Date(data.credential.issue_date).toLocaleDateString();
        } else {
            card.style.display = 'none';
        }

    } catch (err) {
        console.error("Verification error:", err);
        alert("An error occurred during verification.");
    }
}

// Helper: Extract credential ID from a QR code URL or raw text
function extractCredentialIdFromQR(decodedText) {
    // QR payload format: {BASE_URL}/verify/{credential_id}
    const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const match = decodedText.match(uuidRegex);
    return match ? match[0] : decodedText.trim();
}

// Helper: Scan QR code from an image file using Html5Qrcode
async function scanQRFromImageFile(file) {
    if (typeof Html5Qrcode === 'undefined') throw new Error("QR library not loaded");
    const html5QrCode = new Html5Qrcode("qr-reader");
    const decodedText = await html5QrCode.scanFile(file, true);
    return extractCredentialIdFromQR(decodedText);
}

// Helper: Scan QR code from a PDF by rendering each page to canvas
async function scanQRFromPDF(file) {
    if (typeof pdfjsLib === 'undefined') throw new Error("PDF.js library not loaded");
    if (typeof Html5Qrcode === 'undefined') throw new Error("QR library not loaded");

    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const html5QrCode = new Html5Qrcode("qr-reader");

    // Try each page (usually the QR is on page 1)
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: 2.0 }); // High resolution for better QR detection

        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext('2d');

        await page.render({ canvasContext: ctx, viewport: viewport }).promise;

        // Convert canvas to blob and scan
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        const imageFile = new File([blob], "page.png", { type: "image/png" });

        try {
            const decodedText = await html5QrCode.scanFile(imageFile, true);
            return extractCredentialIdFromQR(decodedText);
        } catch (err) {
            // QR not found on this page, try next
            console.log(`No QR found on page ${pageNum}, trying next...`);
        }
    }
    throw new Error("No QR code found in any page of the PDF");
}

// Handle file upload for JSON credentials, PDFs (QR scan), and images (QR scan)
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const inputField = document.getElementById('verifier-id-input');

    // If it's a JSON file, parse it normally
    if (file.name.toLowerCase().endsWith('.json') || file.type === "application/json") {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                if (data && data.id) {
                    inputField.value = data.id;
                    verifyCredential();
                } else {
                    alert("Invalid JSON file. The file must contain an 'id' field.");
                }
            } catch (err) {
                console.error("File parse error:", err);
                alert("Could not parse the JSON file.");
            }
        };
        reader.readAsText(file);

    } else if (file.type.startsWith('image/')) {
        // Scan QR code from uploaded image
        scanQRFromImageFile(file)
            .then(credId => {
                inputField.value = credId;
                verifyCredential();
            })
            .catch(err => {
                console.error("QR scan from image failed:", err);
                alert("No QR code found in the uploaded image. Please upload a certificate with a valid QR code.");
            });

    } else if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        // Scan QR code from PDF by rendering pages
        scanQRFromPDF(file)
            .then(credId => {
                inputField.value = credId;
                verifyCredential();
            })
            .catch(err => {
                console.error("QR scan from PDF failed:", err);
                alert("No QR code found in the uploaded PDF. Please ensure the certificate contains a valid QR code.");
            });

    } else {
        alert("Unsupported file type. Please upload a .json, .pdf, or image file.");
    }
    
    // Reset file input so the same file can be uploaded again if needed
    event.target.value = '';
}

// --- QR SCANNER LOGIC ---
let html5QrcodeScanner = null;

function initQRScanner() {
    if (html5QrcodeScanner) return; // already running

    function onScanSuccess(decodedText, decodedResult) {
        // Stop scanning after a successful read
        stopQRScanner();

        // Inject the scanned text (which is the Credential ID) into the input
        const inputField = document.getElementById('verifier-id-input');
        if (inputField) {
            inputField.value = decodedText.trim();
            // Trigger the verification automatically
            verifyCredential();
        }
    }

    function onScanFailure(error) {
        // Handle scan failure silently to keep scanning frames
    }

    // Initialize the scanner UI in the #qr-reader div
    html5QrcodeScanner = new Html5QrcodeScanner(
      "qr-reader",
      { fps: 10, qrbox: {width: 250, height: 250} },
      /* verbose= */ false);
      
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function stopQRScanner() {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear().catch(error => {
            console.error("Failed to clear scanner: ", error);
        });
        html5QrcodeScanner = null;
    }
}
