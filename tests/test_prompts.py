from unittest.mock import patch

from personio_hacking.prompts import (
    MacPrompt,
    TerminalPrompt,
    get_prompt,
)


def test_terminal_prompt_confirm_yes():
    prompt = TerminalPrompt()
    with patch("builtins.input", return_value="y"):
        assert prompt.confirm(title="Personio", message="Track hours today?") is True


def test_terminal_prompt_confirm_no():
    prompt = TerminalPrompt()
    with patch("builtins.input", return_value="n"):
        assert prompt.confirm(title="Personio", message="Track hours today?") is False


def test_terminal_prompt_confirm_default_yes():
    prompt = TerminalPrompt()
    with patch("builtins.input", return_value=""):
        assert (
            prompt.confirm(title="Personio", message="Track hours today?", default=True)
            is True
        )


def test_mac_prompt_clicked_track():
    prompt = MacPrompt()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "button returned:Track Now\n"
        assert prompt.confirm(title="Personio", message="Track today?") is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"
        assert "display dialog" in args[2]


def test_mac_prompt_clicked_skip():
    prompt = MacPrompt()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "button returned:Skip\n"
        assert prompt.confirm(title="Personio", message="Track today?") is False


def test_mac_prompt_user_canceled_dialog():
    prompt = MacPrompt()
    with patch("subprocess.run") as mock_run:
        # osascript returns non-zero when user presses Escape or closes dialog
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert prompt.confirm(title="Personio", message="Track today?") is False


def test_get_prompt_factory():
    assert isinstance(get_prompt("terminal"), TerminalPrompt)
    assert isinstance(get_prompt("dialog"), MacPrompt)

    with patch("platform.system", return_value="Darwin"):
        assert isinstance(get_prompt("auto"), MacPrompt)

    with patch("platform.system", return_value="Linux"):
        assert isinstance(get_prompt("auto"), TerminalPrompt)
