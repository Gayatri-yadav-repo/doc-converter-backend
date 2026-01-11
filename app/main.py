from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import subprocess
import os
import shutil
import uuid

app = FastAPI(
    title="Smart Document Converter API",
    description="Upload a document, see detected format, and convert it to PDF, Word, or PowerPoint",
    version="1.1.0"
)

# ----------------------
# CONFIG
# ----------------------
LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Supported conversion map
SUPPORTED_FORMATS = {
    "docx": ["pdf", "pptx"],
    "pdf": ["docx", "pptx"],
    "pptx": ["pdf"]
}


# ----------------------
# HELPERS
# ----------------------
def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower()


def convert_file(input_path: str, output_format: str):
    subprocess.run(
        [
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to",
            output_format,
            input_path,
            "--outdir",
            OUTPUT_DIR
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


# ----------------------
# SMART CONVERT ENDPOINT
# ----------------------
@app.post("/convert")
async def smart_convert(
    file: UploadFile = File(...),
    target_format: str = Form(
        ...,
        description="Target output format (pdf, docx, pptx)"
    )
):
    # Detect formats
    input_format = get_extension(file.filename)
    target_format = target_format.lower()

    # ❌ Unsupported input
    if input_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Input format '{input_format}' is not supported"
        )

    # ❌ Unsupported target
    if target_format not in ["pdf", "docx", "pptx"]:
        raise HTTPException(
            status_code=400,
            detail=f"Target format '{target_format}' is not supported"
        )

    # ❌ Same format
    if input_format == target_format:
        raise HTTPException(
            status_code=400,
            detail="Input and target formats are the same"
        )

    # ❌ Unsupported conversion path
    if target_format not in SUPPORTED_FORMATS[input_format]:
        raise HTTPException(
            status_code=400,
            detail=f"Conversion from {input_format} to {target_format} is not supported"
        )

    # Save file
    uid = uuid.uuid4().hex
    safe_name = f"{uid}_{file.filename}"
    input_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Try direct conversion
    convert_file(input_path, target_format)

    output_file = os.path.splitext(safe_name)[0] + f".{target_format}"
    output_path = os.path.join(OUTPUT_DIR, output_file)

    # ----------------------
    # Fallback: Word → PDF → PPT
    # ----------------------
    if not os.path.exists(output_path):
        if input_format == "docx" and target_format == "pptx":
            convert_file(input_path, "pdf")
            pdf_path = os.path.join(
                OUTPUT_DIR,
                os.path.splitext(safe_name)[0] + ".pdf"
            )

            if not os.path.exists(pdf_path):
                raise HTTPException(
                    status_code=400,
                    detail="Word to PDF conversion failed"
                )

            convert_file(pdf_path, "pptx")
            ppt_path = pdf_path.replace(".pdf", ".pptx")

            if not os.path.exists(ppt_path):
                raise HTTPException(
                    status_code=400,
                    detail="Word to PPT conversion failed due to unsupported layout"
                )

            return FileResponse(
                ppt_path,
                filename=os.path.basename(ppt_path),
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={
                    "X-Input-Format": input_format,
                    "X-Target-Format": target_format
                }
            )

        # ❌ Conversion failed (but handled safely)
        raise HTTPException(
            status_code=400,
            detail="Conversion failed. File content may be unsupported"
        )

    # ✅ Success response
    return FileResponse(
        output_path,
        filename=output_file,
        media_type="application/octet-stream",
        headers={
            "X-Input-Format": input_format,
            "X-Target-Format": target_format
        }
    )
