import qrcode
import os

def generate_qr(code, ticket_id):
    os.makedirs("static/qr",exist_ok=True)
    filename =f"static/qr/ticket_{ticket_id}.png"

    image = qrcode.make(code)
    image.save(filename)
    return filename