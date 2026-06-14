import os
from uuid import uuid4

UPLOAD_DIR = "temp_uploads"


def save_file(file, content: bytes):
    try:
        # Ensure folder exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Unique filename
        unique_name = f"{uuid4()}_{file.filename}"

        # Absolute path
        file_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_name))

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        return file_path

    except Exception as e:
        raise Exception(f"File saving failed: {str(e)}")