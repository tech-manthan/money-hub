import zipfile

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from moneyhub.cli import app as cli
from moneyhub.listing import platforms
from moneyhub.pipeline import Request, generate
from moneyhub.web.app import app

MB = 1_000_000


def _folder(tmp_path, sizes_mb):
    (tmp_path / "product").mkdir()
    for i, s in enumerate(sizes_mb):
        with open(tmp_path / "product" / f"file-{i}.pdf", "wb") as f:
            f.truncate(int(s * MB))
    return tmp_path


def test_files_that_fit_are_sold_as_they_are(tmp_path):
    p = platforms.plan(_folder(tmp_path, [3, 5]), "etsy")
    assert p["strategy"] == "as they are" and [d["name"] for d in p["downloads"]] == ["file-0.pdf", "file-1.pdf"] and not [w for w in p["warnings"] if "too big" in w]


def test_etsy_groups_files_into_zips_of_20_mb_or_less_when_there_are_too_many(tmp_path):
    p = platforms.plan(_folder(tmp_path, [9, 9, 9, 9, 9, 9, 9]), "etsy")   # 7 files: over the 5 file limit, 63 MB in total
    assert p["strategy"] == "grouped into zips" and all(d["ok"] and d["size"] <= 20 * MB for d in p["downloads"]) and len(p["downloads"]) <= 5
    assert sorted(n for d in p["downloads"] for n in d["from"]) == sorted(f"file-{i}.pdf" for i in range(7))


def test_a_file_over_the_limit_is_flagged_not_hidden(tmp_path):
    p = platforms.plan(_folder(tmp_path, [25, 2]), "etsy")
    assert not p["ok"] and any("file-0.pdf" in w and "20 MB" in w for w in p["warnings"]) and any(not d["ok"] for d in p["downloads"])
    assert platforms.plan(tmp_path, "gumroad")["downloads"][0]["ok"]   # the same file is fine on a platform with a bigger limit


def test_unknown_platform_is_refused(tmp_path):
    with pytest.raises(ValueError, match="unknown platform"):
        platforms.plan(tmp_path, "amazon")


@pytest.fixture()
def made():
    return generate(Request("nurse", "checklist_pack", providers=["builtin"], seed=2, sizes=["letter"], with_images=False, with_video=False, options={"no_research": True}))


@pytest.mark.parametrize("platform", list(platforms.PLATFORMS))
def test_each_platform_pack_has_the_download_text_and_readme(made, platform):
    z = platforms.build_pack(made.folder, platform)
    names = zipfile.ZipFile(z).namelist()
    assert "README.txt" in names and any(n.startswith("1-DOWNLOAD/") for n in names) and any(n.startswith("3-LISTING-TEXT/") for n in names)


def test_web_endpoints_preview_files_and_download_a_pack(made):
    c = TestClient(app)
    pid = made.product_id
    page = c.get(f"/product/{pid}")
    assert page.status_code == 200 and 'id="viewer"' in page.text and 'id="sell-platform"' in page.text and 'data-view="files"' in page.text
    plan = c.get(f"/api/product/{pid}/platform/etsy").json()
    assert plan["label"] == "Etsy" and plan["downloads"]
    assert c.get(f"/api/product/{pid}/platform/amazon").status_code == 404
    z = c.get(f"/product/{pid}/pack/gumroad.zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    pdf = next(d["name"] for d in plan["downloads"] if d["name"].endswith(".pdf"))
    info = c.get(f"/api/product/{pid}/inspect", params={"path": f"product/{pdf}"}).json()
    assert info["kind"] == "pdf" and info["pages"] >= 1
    assert c.get(f"/api/product/{pid}/inspect", params={"path": "upload-package.zip"}).json()["kind"] == "zip"
    assert c.get(f"/api/product/{pid}/inspect", params={"path": "../../../etc/passwd"}).status_code == 404


def test_cli_makes_a_pack(made):
    r = CliRunner().invoke(cli, ["export", "pack", str(made.product_id), "payhip"])
    assert r.exit_code == 0 and "Payhip pack" in r.output
    assert CliRunner().invoke(cli, ["export", "pack", str(made.product_id), "bogus"]).exit_code != 0
