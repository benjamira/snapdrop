from datetime import datetime

import naming


def test_clean_title():
    assert naming.clean_title('  Rechnung: Bau/Haus*?  ') == "Rechnung Bau Haus"
    assert naming.clean_title("a\tb\nc") == "a b c"
    assert naming.clean_title("Ende...") == "Ende"
    assert naming.clean_title("Zähler: Nov/2026") == "Zähler Nov 2026"
    assert naming.clean_title("a\x00b") == "ab"
    assert naming.clean_title(' /\\:*?"<>| ') == ""
    assert len(naming.clean_title("x" * 300)) == 100
    assert naming.clean_title("Über Größe ß") == "Über Größe ß"


def test_file_name():
    ts = datetime(2026, 11, 22, 9, 5, 3)
    assert naming.file_name(ts, 1, "IMG_1.JPEG") == "20261122-090503_01.jpg"
    assert naming.file_name(ts, 12, "image.heic") == "20261122-090503_12.heic"
    assert naming.file_name(ts, 2, None) == "20261122-090503_02.jpg"
    assert naming.file_name(ts, 3, "evil.php<x>") == "20261122-090503_03.jpg"


def test_join():
    assert naming.join("/", "a") == "/a"
    assert naming.join("/Fotos/", "/Titel") == "/Fotos/Titel"
    assert naming.join("") == "/"
