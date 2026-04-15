from __future__ import annotations

from src.city1.district_source_catalog import extract_district_population_options_from_html


def test_extract_district_population_options_from_html_filters_relevant_rows() -> None:
    html = """
    <html>
      <body>
        <select name="name">
          <option value="">Name</option>
          <option value="292564">Численность населения в разрезе районов</option>
          <option value="292565">Численность населения по полу в разрезе районов</option>
          <option value="10704">Естественное движение населения</option>
          <option value="480100">Основные индикаторы рынка труда</option>
        </select>
      </body>
    </html>
    """

    frame = extract_district_population_options_from_html(
        html,
        city_name="Astana",
        catalog_url="https://example.test/astana",
        city_query="Astana, Kazakhstan",
    )

    assert list(frame["option_id"]) == ["292564", "292565"]
    assert all(frame["city_name"] == "Astana")
    assert all(frame["normalized_city_name"] == "astana")


def test_extract_district_population_options_from_html_requires_name_select() -> None:
    try:
        extract_district_population_options_from_html(
            "<html><body><div>No select</div></body></html>",
            city_name="Shymkent",
            catalog_url="https://example.test/shymkent",
            city_query="Shymkent, Kazakhstan",
        )
    except ValueError as exc:
        assert "select[name='name']" in str(exc)
    else:  # pragma: no cover - defensive branch
        raise AssertionError("Expected ValueError when the name select is absent.")
