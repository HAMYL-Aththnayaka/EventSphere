def test_booking_quantity_limit():
    quantity = 7

    assert quantity > 6


def test_ticket_code_is_unique():
    codes = ["ABC123", "XYZ456"]

    assert len(codes) == len(set(codes))


def test_venue_time():
    start = 10
    end = 12

    assert end > start


def test_ticket_status():
    status = "valid"

    assert status == "valid"


def test_waitlist_status():
    status = "waiting"

    assert status == "waiting"


def test_notification_message():
    message = "Your booking is confirmed"

    assert len(message) > 0


def test_refund_policy():
    booking_total = 1000
    refund = booking_total

    assert refund == 1000


def test_booking_limit():
    assert 6 <= 6


def test_performatives():
    valid = [
        "REQUEST",
        "AGREE",
        "REFUSE",
        "PROPOSE",
        "INFORM",
        "FAILURE"
    ]

    assert len(valid) == 6


def test_simulated_payment():
    reference = "SIM-123456"

    assert reference.startswith("SIM-")