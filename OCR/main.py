from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
from pillow_heif import register_heif_opener
import pytesseract
import io
import numpy as np
import cv2
from pdf2image import convert_from_bytes

register_heif_opener()

app = FastAPI()


def preprocess_image(image: Image.Image):
    # Convert PIL image to grayscale numpy array
    img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Light denoise to reduce speckles without blurring text too much
    gray = cv2.medianBlur(gray, 3)

    # Normalize contrast to spread intensity range
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

    # Adaptive threshold handles uneven lighting better than a fixed cutoff
    th = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    return th


def clean_text(text: str):
    return "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )


def run_tesseract_variants(image_array: np.ndarray, lang: str):
    # Try multiple page segmentation modes; keep the longest cleaned result.
    candidate_psms = [4, 6, 11]
    best_text = ""

    for psm in candidate_psms:
        config = f"--oem 1 --psm {psm}"
        raw = pytesseract.image_to_string(image_array, lang=lang, config=config)
        cleaned = clean_text(raw)
        if len(cleaned) > len(best_text):
            best_text = cleaned

    return best_text


@app.post("/ocr")
async def run_ocr(
    data: UploadFile = File(...),
    lang: str = "eng"
):
    try:
        file_bytes = await data.read()
        filename = data.filename.lower()

        # PDF
        if filename.endswith(".pdf"):
            images = convert_from_bytes(file_bytes, dpi=300)
            text_parts = []
            for img in images:
                processed = preprocess_image(img)
                text_parts.append(run_tesseract_variants(processed, lang))
            text = "\n".join(text_parts)

        # Images (jpg, png, heic, etc.)
        else:
            image = Image.open(io.BytesIO(file_bytes))
            processed = preprocess_image(image)
            text = run_tesseract_variants(processed, lang)

        return {
            "filename": data.filename,
            "text": clean_text(text)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
