from pathlib import Path


def test_field_first_da_route_is_explicit():
    source = (Path(__file__).resolve().parents[1] / "app/pages.py").read_text()
    assert '"pages.attendance" if current_user.role == Role.DA' in source
    assert 'if current_user.role == Role.DA:' in source


def test_attendance_is_first_da_navigation_link():
    source = (Path(__file__).resolve().parents[1] / "app/templates/base.html").read_text()
    da_nav = source.split('<nav class="rail-nav">', 1)[1].split('{% else %}', 1)[0]
    assert "url_for('pages.attendance')" in da_nav
    assert "url_for('pages.overview')" not in da_nav
