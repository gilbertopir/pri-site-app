/**
 * resizeImages.js
 * Resizes images before upload using Canvas API.
 * Quality preset read from localStorage — set in Tools page.
 */

const QUALITY_PRESETS = {
    low:    { maxPx: 1200, quality: 0.70 },
    medium: { maxPx: 1600, quality: 0.85 },
    high:   { maxPx: 2000, quality: 0.92 },
};

function getPreset() {
    const key = localStorage.getItem('photoQuality') || 'medium';
    return QUALITY_PRESETS[key] || QUALITY_PRESETS.medium;
}

function resizeImage(file) {
    const preset = getPreset();
    return new Promise((resolve) => {
        const img    = new Image();
        const reader = new FileReader();

        reader.onload = e => { img.src = e.target.result; };

        img.onload = () => {
            let w = img.width;
            let h = img.height;

            if (w > preset.maxPx || h > preset.maxPx) {
                if (w > h) { h = Math.round(h * preset.maxPx / w); w = preset.maxPx; }
                else       { w = Math.round(w * preset.maxPx / h); h = preset.maxPx; }
            }

            const canvas = document.createElement('canvas');
            canvas.width  = w;
            canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);

            canvas.toBlob(blob => {
                resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' }));
            }, 'image/jpeg', preset.quality);
        };

        reader.readAsDataURL(file);
    });
}

async function resizeFiles(files, maxCount) {
    const limited = Array.from(files).slice(0, maxCount || files.length);
    return Promise.all(limited.map(resizeImage));
}
