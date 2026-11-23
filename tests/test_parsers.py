from types import SimpleNamespace

from app.parsers import is_service_message, parse_channel_post_reference, root_message_id


def test_channel_post_reference_parsing():
    assert parse_channel_post_reference("https://t.me/example_channel/105") == ("example_channel", 105)
    assert parse_channel_post_reference("t.me/s/example_channel/42?single") == ("example_channel", 42)
    assert parse_channel_post_reference("not a post") is None
    assert parse_channel_post_reference("105") is None


def test_album_root_id_and_non_album_fallback():
    messages = [SimpleNamespace(id=18, grouped_id=77), SimpleNamespace(id=16, grouped_id=77),
                SimpleNamespace(id=19, grouped_id=None)]
    assert root_message_id(messages, 18) == 16
    assert root_message_id(messages, 19) == 19
    assert root_message_id(messages, 999) == 999


def test_service_message_detection_without_telegram_library():
    class MessageService:
        pass
    assert is_service_message(MessageService())
    assert is_service_message(SimpleNamespace(is_service=True))
    assert not is_service_message(SimpleNamespace(is_service=False))
