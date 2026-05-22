import hashlib
from pathlib import Path

IMAGES_DIR = Path("data/raw/images")

def dedup_images() -> None:
    folders = list(IMAGES_DIR.iterdir())
    for i, folder in enumerate(folders, 1):
        seen = {}
        for img in folder.iterdir():
            digest = hashlib.md5(img.read_bytes()).hexdigest()
            if digest in seen:
                print(f"Deleting duplicate: {img.name}")
                img.unlink()
            else:
                seen[digest] = img
        print(f"Progress: {i}/{len(folders)} folders done")
        
if __name__ == "__main__":
    dedup_images()
