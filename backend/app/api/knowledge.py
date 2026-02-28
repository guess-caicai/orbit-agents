# app/api/knowledge.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.app.api.utils import save_temp_file
from backend.app.dependencies import get_kb_writer

router = APIRouter()


@router.post("/knowledge/text")
async def upsert_text_knowledge(texts: list[str], writer=Depends(get_kb_writer)):
    try:
        writer.upsert_text(texts)
        return {"status": "ok", "count": len(texts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/excel")
async def upsert_excel_knowledge(file: UploadFile = File(...), writer=Depends(get_kb_writer)):
    try:
        path = save_temp_file(file)
        writer.upsert_excel(path)
        return {"status": "ok", "file": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/pdf")
async def upsert_pdf_knowledge(file: UploadFile = File(...), writer=Depends(get_kb_writer)):
    try:
        path = save_temp_file(file)
        writer.upsert_pdf(path)
        return {"status": "ok", "file": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/image")
async def upsert_image_knowledge(files: list[UploadFile] = File(...), writer=Depends(get_kb_writer)):
    try:
        paths = [save_temp_file(f) for f in files]
        writer.upsert_image(paths)
        return {"status": "ok", "count": len(paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
