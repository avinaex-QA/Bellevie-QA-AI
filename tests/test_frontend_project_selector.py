from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_multiselect_markup_exists():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Select Project" in html
    assert 'id="project-multiselect"' in html
    assert 'id="selected-projects"' in html
    assert 'id="project-search"' in html
    assert 'id="add-project-btn"' in html
    assert "Project Context" in html
    assert "Select Module" in html
    assert 'id="module-multiselect"' in html
    assert 'id="selected-modules"' in html
    assert 'id="module-search"' in html
    assert 'id="add-module-btn"' in html
    assert "Module Context" in html
    assert "ClickUp" in html
    assert 'id="clickup-task-id"' in html
    assert 'id="fetch-clickup-btn"' in html
    assert 'id="clickup-preview"' in html


def test_frontend_sends_selected_projects_modules_and_validates_source():
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert "PROJECT_OPTIONS" not in app_js
    assert "MODULE_OPTIONS" not in app_js
    assert "PROJECT_STORAGE_KEY" in app_js
    assert "MODULE_STORAGE_KEY" in app_js
    assert "MAX_MANAGED_OPTIONS = 50" in app_js
    assert "Maximum 50 projects allowed" in app_js
    assert "Maximum 50 modules allowed" in app_js
    assert "addManagedOption" in app_js
    assert "deleteManagedOption" in app_js
    assert "formData.append('selected_projects', project)" in app_js
    assert "formData.append('selected_modules', moduleName)" in app_js
    assert "formData.append('clickup_task_id', clickupTaskId)" in app_js
    assert "/api/clickup/task/" in app_js
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


def test_frontend_uses_profile_avatar_dropdown_in_header():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert 'id="profile-avatar-btn"' in html
    assert 'id="profile-dropdown"' in html
    assert 'id="profile-settings-item"' in html
    assert 'id="profile-logout-item"' in html
    assert 'id="settings-btn"' not in html
    assert 'id="profile-pill"' not in html
    assert 'id="logout-btn"' not in html
    assert "getProfileInitial" in app_js
    assert "closeProfileMenu" in app_js
