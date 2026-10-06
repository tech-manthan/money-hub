from typer.testing import CliRunner

from moneyhub.cli import app
from moneyhub.design import choose_style

runner = CliRunner()


def test_choose_style_pins_only_what_is_asked():
    free = choose_style(seed=5)
    pinned = choose_style(seed=5, header="box", radius=0, grid="dashed")
    assert (pinned.header, pinned.radius, pinned.grid) == ("box", 0, "dashed")
    assert pinned.palette.key == free.palette.key and pinned.fonts.key == free.fonts.key


def test_styles_command_lists_every_knob():
    out = runner.invoke(app, ["styles"]).output
    for word in ("--palette", "--fonts", "--header", "--radius", "--grid", "--motif", "--page-layout", "wall_art", "stacked", "--art-provider"):
        assert word in out


def test_make_rejects_unknown_option_values():
    r = runner.invoke(app, ["make", "nurse", "wall_art", "--fonts", "nope", "--llm", "builtin"])
    assert r.exit_code != 0 and "editorial" in r.output
    r = runner.invoke(app, ["make", "nurse", "wall_art", "--motif", "nope", "--llm", "builtin"])
    assert r.exit_code != 0


def test_make_applies_style_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_OUT", str(tmp_path))
    r = runner.invoke(app, ["make", "nurse", "weekly_planner", "--llm", "builtin", "--no-images", "--no-video", "--no-research",
                            "--palette", "plum", "--fonts", "classic", "--header", "box", "--radius", "0", "--grid", "dotted", "--seed", "3"])
    assert r.exit_code == 0, r.output
