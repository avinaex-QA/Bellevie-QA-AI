from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_multiselect_markup_exists():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Select Project" in html
    assert 'id="project-multiselect"' in html
    assert 'id="selected-projects"' in html
    assert 'id="project-search"' in html
    assert "Project Context" in html
    assert "Select Module" in html
    assert 'id="module-multiselect"' in html
    assert 'id="selected-modules"' in html
    assert 'id="module-search"' in html
    assert "Module Context" in html


def test_frontend_sends_selected_projects_modules_and_validates_source():
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert "PROJECT_OPTIONS" in app_js
    assert "MODULE_OPTIONS" in app_js
    assert "Resident APP" in app_js
    assert "Billing & Account" in app_js
    assert "Marketplace Master Dashboard" in app_js
    assert "formData.append('selected_projects', project)" in app_js
    assert "formData.append('selected_modules', moduleName)" in app_js
    assert "Select project, module, and requirement source" in app_js
    assert "renderHistoryProjects" in app_js


def test_frontend_has_execution_and_raise_bug_controls():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert "Raise Jira Bug" in html
    assert 'id="bug-modal-overlay"' in html
    assert "Execution" in html
    assert "Raise Bug" in app_js
    assert "/api/jira/bug-draft" in app_js
    assert "/api/jira/create-bug" in app_js
    assert "SESSION_STORAGE_KEY" in app_js
