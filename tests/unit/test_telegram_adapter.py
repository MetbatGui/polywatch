"""TelegramAdapter 단위 테스트"""
from src.infrastructure.telegram_adapter import TelegramAdapter


def test_send_posts_to_telegram(mocker):
    resp = mocker.Mock()
    resp.raise_for_status = mocker.Mock()
    mock_post = mocker.patch("requests.post", return_value=resp)

    adapter = TelegramAdapter(token="tok123", chat_id="chat456")
    adapter.send("hello world")

    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert "tok123" in url
    assert mock_post.call_args[1]["json"]["chat_id"] == "chat456"
    assert mock_post.call_args[1]["json"]["text"] == "hello world"


def test_send_raises_on_http_error(mocker):
    import requests
    resp = mocker.Mock()
    resp.raise_for_status.side_effect = requests.HTTPError("bad")
    mocker.patch("requests.post", return_value=resp)

    adapter = TelegramAdapter(token="t", chat_id="c")
    try:
        adapter.send("test")
        assert False, "Should raise"
    except requests.HTTPError:
        pass
