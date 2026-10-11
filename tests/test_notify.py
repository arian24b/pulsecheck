from unittest import mock

from pulsecheck import notify

IMG = "nickfedor/shoutrrr:x"


def test_command_modes():
    assert notify.command("docker", IMG) == ["docker", "run", "--rm", IMG]
    assert notify.command("/opt/sh", IMG) == ["/opt/sh"]
    with mock.patch.object(notify, "_docker_ok", return_value=True):
        assert notify.command("auto", IMG)[0] == "docker"
    with mock.patch.object(notify, "_docker_ok", return_value=False):
        assert notify.command("auto", IMG) == ["shoutrrr"]


def test_send_survives_missing_binary(capsys):
    notify.send(["/nonexistent/shoutrrr"], ["logger://"], "hi")
    assert "notify failed" in capsys.readouterr().err
