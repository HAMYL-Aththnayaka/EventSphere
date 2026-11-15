import base64

from app.qr import generate_qr


def test_ticket_qr_is_returned_without_filesystem_storage():
    qr_data_uri = generate_qr("unguessable-ticket-code")
    header, encoded = qr_data_uri.split(",", 1)

    assert header == "data:image/png;base64"
    assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")
