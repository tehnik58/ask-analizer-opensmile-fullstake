from app.charts import render_lld_chart


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_render_full_lld_png():
    lld = {
        "F0": [45.2, None, 46.1, 44.0],
        "Loudness": [0.01, 0.02, None, 0.03],
        "Jitter": [0.02, 0.021, 0.019, None],
    }
    png = render_lld_chart(lld, duration_sec=0.04)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 1000


def test_render_partial_metrics():
    png = render_lld_chart({"F0": [1.0, 2.0]}, duration_sec=0.02)
    assert png.startswith(PNG_MAGIC)


def test_render_empty_raises():
    import pytest

    with pytest.raises(ValueError):
        render_lld_chart({}, 1.0)
    with pytest.raises(ValueError):
        render_lld_chart({"F0": []}, 1.0)
