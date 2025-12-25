from pathlib import Path
import shutil

from django.core.files import File
from django.core.files.storage import default_storage


def stage_to_local(file_field, work_dir: Path, name: str) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(file_field, "path"):
        try:
            local_path = Path(file_field.path)
            if local_path.exists():
                return local_path
        except Exception:
            pass
    local_path = work_dir / name
    with default_storage.open(file_field.name, "rb") as src, open(
        local_path, "wb"
    ) as dst:
        shutil.copyfileobj(src, dst)
    return local_path


def save_from_local(local_path: Path, destination: str) -> str:
    with open(local_path, "rb") as src:
        return default_storage.save(destination, File(src))
