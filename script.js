document.addEventListener('DOMContentLoaded', () => {
    const API_URL = 'http://localhost:5000/api';

    // ── NAVIGATION & UI ──
    const navLinks = document.querySelectorAll('.nav-link, .mob-link');
    const sections = document.querySelectorAll('section');
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobile-menu');

    window.addEventListener('scroll', () => {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= (sectionTop - 200)) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').includes(current)) {
                link.classList.add('active');
            }
        });
    });

    hamburger.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
        hamburger.classList.toggle('active');
    });

    // ── ELDERLY MODE ──
    const elderlyFab = document.getElementById('elderly-fab');
    elderlyFab.addEventListener('click', () => {
        document.body.classList.toggle('elderly-mode');
        showToast(document.body.classList.contains('elderly-mode') ? 'Elderly Mode Enabled' : 'Standard Mode Enabled');
    });

    // ── UPLOAD & OCR ──
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const chooseBtn = document.getElementById('choose-btn');
    const previewBox = document.getElementById('preview-box');
    const previewImg = document.getElementById('preview-img');
    const reuploadBtn = document.getElementById('reupload-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const ocrCard = document.getElementById('ocr-card');
    const ocrEmpty = document.getElementById('ocr-empty');
    const ocrResult = document.getElementById('ocr-result');
    const ocrLoading = document.getElementById('ocr-loading');
    const medicinesList = document.getElementById('medicines-list');
    const patientInfo = document.getElementById('patient-info');
    const simplifiedInstructions = document.getElementById('simplified-instructions');
    const langSelect = document.getElementById('lang-select');
    const readAloudBtn = document.getElementById('read-aloud-btn');

    let selectedFile = null;
    let currentRxAudio = null;

    chooseBtn.addEventListener('click', () => fileInput.click());
    reuploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            selectedFile = files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImg.src = e.target.result;
                previewBox.classList.remove('hidden');
                dropZone.classList.add('hidden');
                analyzeBtn.disabled = false;
            };
            reader.readAsDataURL(selectedFile);
        }
    }

    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        ocrEmpty.classList.add('hidden');
        ocrResult.classList.add('hidden');
        ocrLoading.classList.remove('hidden');
        analyzeBtn.disabled = true;

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('language', langSelect.selectedOptions[0].text.split(' ')[0]);

        try {
            const response = await fetch(`${API_URL}/analyze`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            displayOCRResult(data);
            fetchHistory(); // Refresh history
        } catch (err) {
            showToast('Error analyzing prescription: ' + err.message, 'error');
        } finally {
            ocrLoading.classList.add('hidden');
            analyzeBtn.disabled = false;
        }
    });

    function displayOCRResult(data) {
        ocrResult.classList.remove('hidden');
        medicinesList.innerHTML = '';
        
        data.medicines.forEach(med => {
            const div = document.createElement('div');
            div.className = 'med-item';
            div.innerHTML = `
                <h5>${med.name} (${med.dosage})</h5>
                <p><i class="fa-solid fa-clock"></i> ${med.frequency} for ${med.duration}</p>
                <p><i class="fa-solid fa-info-circle"></i> ${med.instructions}</p>
            `;
            medicinesList.appendChild(div);
        });

        simplifiedInstructions.innerHTML = data.instructions.replace(/\n/g, '<br>');
        currentRxAudio = data.audio_url;
        readAloudBtn.disabled = !currentRxAudio;
    }

    readAloudBtn.addEventListener('click', () => {
        if (currentRxAudio) {
            const audio = new Audio(`http://localhost:5000${currentRxAudio}`);
            audio.play();
        }
    });

    // ── VOICE ASSISTANT ──
    const micBtn = document.getElementById('mic-btn');
    const voiceOrb = document.getElementById('voice-orb');
    const statusText = document.getElementById('status-text');
    const voiceTranscript = document.getElementById('voice-transcript');
    const voiceResponse = document.getElementById('voice-response');
    const langPills = document.querySelectorAll('.lang-pill');

    let selectedVoiceLang = 'en-IN';
    let recognition = null;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            voiceOrb.classList.add('active');
            statusText.textContent = 'Listening...';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            voiceTranscript.innerHTML = `<p>"${transcript}"</p>`;
            processVoiceQuery(transcript);
        };

        recognition.onerror = (event) => {
            stopMic();
            // Silent handling for common non-critical issues
            if (['no-speech', 'aborted', 'network'].includes(event.error)) return;
            
            if (event.error === 'not-allowed') {
                showToast('Please allow microphone access in your settings.', 'error');
            } else {
                showToast('Voice Assistant is busy. Please try again in a moment.', 'error');
            }
        };

        recognition.onend = () => {
            stopMic();
        };
    }

    micBtn.addEventListener('click', () => {
        if (voiceOrb.classList.contains('active')) {
            recognition.stop();
        } else {
            startMic();
        }
    });

    function startMic() {
        if (!recognition) {
            showToast('Speech recognition not supported in this browser', 'error');
            return;
        }
        recognition.lang = selectedVoiceLang;
        recognition.start();
    }

    function stopMic() {
        voiceOrb.classList.remove('active');
        statusText.textContent = 'Tap the mic to start';
    }

    async function processVoiceQuery(query) {
        statusText.textContent = 'Processing...';
        try {
            const response = await fetch(`${API_URL}/voice-query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: query,
                    language: document.querySelector('.lang-pill.active').dataset.label || 'English'
                })
            });
            const data = await response.json();
            voiceResponse.innerHTML = `<p>${data.answer}</p>`;
            if (data.audio_url) {
                const audio = new Audio(`http://localhost:5000${data.audio_url}`);
                audio.play();
            }
        } catch (err) {
            showToast('Voice processing failed', 'error');
        } finally {
            statusText.textContent = 'Ready';
        }
    }

    langPills.forEach(pill => {
        pill.addEventListener('click', () => {
            langPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedVoiceLang = pill.dataset.lang;
        });
    });

    // ── REMINDERS ──
    const medName = document.getElementById('med-name');
    const medDose = document.getElementById('med-dose');
    const medTime = document.getElementById('med-time');
    const medMeal = document.getElementById('med-meal');
    const addReminderBtn = document.getElementById('add-reminder-btn');
    const remindersContainer = document.getElementById('reminders-container');

    async function fetchReminders() {
        const response = await fetch(`${API_URL}/reminders`);
        const data = await response.json();
        renderReminders(data);
    }

    function renderReminders(reminders) {
        remindersContainer.innerHTML = '';
        let morning = 0, afternoon = 0, night = 0;

        reminders.forEach(r => {
            if (r.timing === 'Morning') morning++;
            if (r.timing === 'Afternoon') afternoon++;
            if (r.timing === 'Night') night++;

            const div = document.createElement('div');
            div.className = 'med-item';
            div.style.display = 'flex';
            div.style.justifyContent = 'space-between';
            div.style.alignItems = 'center';
            div.style.marginBottom = '10px';
            div.innerHTML = `
                <div>
                    <h5 style="margin:0">${r.med_name} (${r.dose})</h5>
                    <p style="margin:0;font-size:0.8rem">${r.timing} • ${r.meal}</p>
                </div>
                <button class="btn btn-sm btn-outline" onclick="deleteReminder(${r.id})">
                    <i class="fa-solid fa-trash"></i>
                </button>
            `;
            remindersContainer.appendChild(div);
        });

        document.getElementById('morning-count').textContent = `${morning} medicines`;
        document.getElementById('afternoon-count').textContent = `${afternoon} medicines`;
        document.getElementById('night-count').textContent = `${night} medicines`;
        
        // Update progress (simulation)
        const total = reminders.length;
        const pct = total > 0 ? 60 : 0; // Simulated progress
        document.getElementById('progress-pct').textContent = `${pct}%`;
        document.getElementById('circle-fill').style.strokeDasharray = `${pct}, 100`;
    }

    addReminderBtn.addEventListener('click', async () => {
        if (!medName.value) return;
        const body = {
            med_name: medName.value,
            dose: medDose.value,
            timing: medTime.value,
            meal: medMeal.value
        };
        await fetch(`${API_URL}/reminders`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        medName.value = ''; medDose.value = '';
        fetchReminders();
    });

    window.deleteReminder = async (id) => {
        await fetch(`${API_URL}/reminders/${id}`, { method: 'DELETE' });
        fetchReminders();
    };

    // ── HISTORY ──
    const historyGrid = document.getElementById('history-grid');
    const historyEmpty = document.getElementById('history-empty');

    async function fetchHistory() {
        const response = await fetch(`${API_URL}/history`);
        const data = await response.json();
        renderHistory(data);
    }

    function renderHistory(history) {
        historyGrid.innerHTML = '';
        if (history.length === 0) {
            historyEmpty.classList.remove('hidden');
            return;
        }
        historyEmpty.classList.add('hidden');

        history.forEach(rx => {
            const card = document.createElement('div');
            card.className = 'feat-card'; // Reuse styling
            card.style.background = 'white';
            card.style.border = '1px solid var(--border)';
            card.style.borderRadius = '12px';
            card.style.textAlign = 'left';
            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; margin-bottom:10px">
                    <span style="font-size:0.8rem; color:var(--text-muted)">${rx.date}</span>
                    <button class="btn btn-sm" onclick="deleteHistory(${rx.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
                <h4>${rx.patient}</h4>
                <p>${rx.medicines.length} medicines extracted</p>
                ${rx.audio_url ? `<button class="btn btn-sm btn-primary mt-4" onclick="playAudio('${rx.audio_url}')"><i class="fa-solid fa-play"></i> Listen</button>` : ''}
            `;
            historyGrid.appendChild(card);
        });
    }

    window.deleteHistory = async (id) => {
        await fetch(`${API_URL}/history/${id}`, { method: 'DELETE' });
        fetchHistory();
    };

    window.playAudio = (url) => {
        new Audio(`http://localhost:5000${url}`).play();
    };

    // ── INITIALIZE ──
    fetchReminders();
    fetchHistory();

    function showToast(msg, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.background = type === 'success' ? '#10b981' : '#ef4444';
        toast.style.color = 'white';
        toast.style.padding = '12px 24px';
        toast.style.borderRadius = '99px';
        toast.style.zIndex = '10000';
        toast.style.boxShadow = '0 10px 20px rgba(0,0,0,0.2)';
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
});
