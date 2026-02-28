# app/api/utils.py
import tempfile
import shutil
from fastapi import UploadFile


def save_temp_file(file: UploadFile) -> str:
    suffix = file.filename.split(".")[-1]
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}")
    with temp as f:
        shutil.copyfileobj(file.file, f.file)
    return temp.name
