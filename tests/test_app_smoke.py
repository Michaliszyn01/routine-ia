def test_import_does_not_create_global_runtime_app():
    import app as app_module

    assert app_module._app_instance is None


def test_create_app_registers_core_routes(flask_app):
    rules = {rule.rule for rule in flask_app.url_map.iter_rules()}

    assert "/" in rules
    assert "/api/dashboard" in rules
    assert "/api/today" in rules
    assert "/api/reports/weekly" in rules


def test_html_pages_smoke(client):
    for path in ["/", "/today", "/settings"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b"html" in response.data.lower()
