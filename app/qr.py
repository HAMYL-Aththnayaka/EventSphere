
from pathlib import Path

import qrcode

BASE_DIR = Path(__file__).resolve().parent
QR_DIRECTORY = BASE_DIR / "static" / "qr"


def generate_qr(code, ticket_id):
    QR_DIRECTORY.mkdir(parents=True, exist_ok=True)

    filename = f"ticket_{ticket_id}.png"
    file_path = QR_DIRECTORY / filename

    image = qrcode.make(code)
    image.save(file_path)

    return f"/static/qr/{filename}"
