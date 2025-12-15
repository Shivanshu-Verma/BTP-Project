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
    img = np.array(image)
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY)[1]
    return img


def clean_text(text: str):
    return "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )


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
            images = convert_from_bytes(file_bytes)
            text = ""
            for img in images:
                processed = preprocess_image(img)
                text += pytesseract.image_to_string(
                    processed,
                    lang=lang,
                    config="--psm 6"
                )

        # Images (jpg, png, heic, etc.)
        else:
            image = Image.open(io.BytesIO(file_bytes))
            processed = preprocess_image(image)
            text = pytesseract.image_to_string(
                processed,
                lang=lang,
                config="--psm 6"
            )

        return {
            "filename": data.filename,
            "text": clean_text(text)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
