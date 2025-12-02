document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('textInput');
    const charCount = document.getElementById('charCount');
    const addPauseBtn = document.getElementById('addPauseBtn');
    const languageSelect = document.getElementById('languageSelect');
    const genderSelect = document.getElementById('genderSelect');
    const genderNote = document.getElementById('genderNote');
    const pitchRange = document.getElementById('pitchRange');
    const speedRange = document.getElementById('speedRange');
    const pitchValue = document.getElementById('pitchValue');
    const speedValue = document.getElementById('speedValue');
    const generateBtn = document.getElementById('generateBtn');
    const loading = document.getElementById('loading');
    const resultArea = document.getElementById('resultArea');
    const audioPlayer = document.getElementById('audioPlayer');
    const downloadLink = document.getElementById('downloadLink');

    // Char Counter
    textInput.addEventListener('input', () => {
        const len = textInput.value.length;
        charCount.innerText = `${len} / 10000`;
        if (len > 10000) charCount.classList.replace('bg-secondary', 'bg-danger');
        else charCount.classList.replace('bg-danger', 'bg-secondary');
    });

    // Pause Button
    addPauseBtn.addEventListener('click', () => {
        const cursorPosition = textInput.selectionStart;
        const text = textInput.value;
        const newText = text.slice(0, cursorPosition) + " [pause] " + text.slice(cursorPosition);
        textInput.value = newText;
        textInput.focus();
    });

    // Slider Updates
    const updateSliders = () => {
        pitchValue.innerText = pitchRange.value;
        speedValue.innerText = speedRange.value;
    };
    pitchRange.addEventListener('input', updateSliders);
    speedRange.addEventListener('input', updateSliders);

    // Special Voice Logic
    languageSelect.addEventListener('change', () => {
        const val = languageSelect.value;
        if(['story', 'horror', 'cartoon', 'news'].includes(val)) {
            genderSelect.disabled = true;
            genderNote.style.display = 'block';
        } else {
            genderSelect.disabled = false;
            genderNote.style.display = 'none';
        }

        if (val === 'horror') { pitchRange.value = -20; speedRange.value = -10; }
        else if (val === 'cartoon') { pitchRange.value = 25; speedRange.value = 0; }
        else if (val === 'story') { pitchRange.value = -5; speedRange.value = -5; }
        else { pitchRange.value = 0; speedRange.value = 0; }
        updateSliders();
    });

    // Generate Request
    generateBtn.addEventListener('click', async () => {
        const text = textInput.value;
        if (!text) return alert("Please type something!");
        if (text.length > 10000) return alert("Text is too long!");

        loading.classList.remove('d-none');
        resultArea.classList.add('d-none');
        generateBtn.disabled = true;

        const data = {
            text: text,
            language: languageSelect.value,
            gender: genderSelect.value,
            pitch: parseInt(pitchRange.value),
            speed: parseInt(speedRange.value)
        };

        try {
            const res = await fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();

            if (result.success) {
                audioPlayer.src = result.file_url;
                downloadLink.href = result.file_url;
                downloadLink.setAttribute('download', result.filename);
                resultArea.classList.remove('d-none');
                audioPlayer.play();
            } else {
                alert(result.error || "Error generating audio");
            }
        } catch (err) {
            alert("Something went wrong!");
        } finally {
            loading.classList.add('d-none');
            generateBtn.disabled = false;
        }
    });
});
