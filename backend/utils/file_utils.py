import os

UPLOAD_ROOT = "uploads"


def save_file(file, user_id: str, bill_id: str) -> str:
    user_dir = os.path.join(UPLOAD_ROOT, user_id)
    os.makedirs(user_dir, exist_ok=True)

    path = os.path.join(user_dir, f"{bill_id}_{file.filename}")

    with open(path, "wb") as f:
        f.write(file.file.read())

    return path
