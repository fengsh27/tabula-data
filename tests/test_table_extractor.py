
from extractor.html_table_extractor import HtmlTableExtractor

def test_HtmlTableExtractor_31206433():
    extractor = HtmlTableExtractor()
    with open("./tests/31206433.html", "r") as fobj:
        html = fobj.read()
        tables = extractor.extract_tables(html)
        assert len(tables) == 5
        assert len(tables[0]['caption']) == 0
        assert len(tables[0]['footnote']) == 0
        assert len(tables[1]['caption']) > 0
        assert len(tables[1]['footnote']) > 0
        assert len(tables[2]['caption']) > 0
        assert len(tables[2]['footnote']) > 0
        assert len(tables[3]['caption']) > 0
        assert len(tables[3]['footnote']) > 0
        assert len(tables[4]['caption']) == 0
        assert len(tables[4]['footnote']) == 0

def test_HtmlTableExtractor_17158945():
    extractor = HtmlTableExtractor()
    with open("./tests/17158945.html", "r") as fobj:
        html = fobj.read()
        tables = extractor.extract_tables(html)
        assert len(tables) > 0

def test_HtmlTableExtractor_15601346():
    extractor = HtmlTableExtractor()
    with open("./tests/15601346.html", "r") as fobj:
        html = fobj.read()
        tables = extractor.extract_tables(html)
        assert len(tables) == 1
        assert len(tables[0]['caption']) > 0
        assert len(tables[0]['footnote']) > 0

