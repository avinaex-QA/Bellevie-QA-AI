from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_multiselect_markup_exists():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Select Project" in html
    assert 'id="project-multiselect"' in html
    assert 'id="selected-projects"' in html
    assert 'id="project-search"' in html
    assert "Project Context" in html


def test_frontend_sends_selected_projects_and_validates_source():
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert "PROJECT_OPTIONS" in app_js
    assert "Resident APP" in app_js
    assert "Marketplace Master Dashboard" in app_js
    assert "formData.append('selected_projects', project)" in app_js
    assert "Select project and requirement source" in app_js
    assert "renderHistoryProjects" in app_js
