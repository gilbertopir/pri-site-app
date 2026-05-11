/**
 * resizeImages.js
 * Resizes an array of File objects using Canvas API before upload.
 * Max 1200px on longest side, JPEG quality 0.8
 */

const MAX_PX      = 1200;
const JPEG_QUALITY = 0.80;

function resizeImage(file) {
    return new Promise((resolve) => {
        const img    = new Image();
        const reader = new FileReader();

        reader.onload = e => { img.src = e.target.result; };

        img.onload = () => {
            let w = img.width;
            let h = img.height;

            if (w > MAX_PX || h > MAX_PX) {
                if (w > h) { h = Math.round(h * MAX_PX / w); w = MAX_PX; }
                else       { w = Math.round(w * MAX_PX / h); h = MAX_PX; }
            }

            const canvas    = document.createElement('canvas');
            canvas.width    = w;
            canvas.height   = h;
            const ctx       = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, w, h);

            canvas.toBlob(blob => {
                resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' }));
            }, 'image/jpeg', JPEG_QUALITY);
        };

        reader.readAsDataURL(file);
    });
}

async function resizeFiles(files, maxCount = 3) {
    const limited = Array.from(files).slice(0, maxCount);
    return Promise.all(limited.map(resizeImage));
}
