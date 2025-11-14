# PUBLIC_INTERFACE
def test_app_import_and_factory():
    """Smoke test to ensure Flask app imports and factory returns an app instance."""
    from app import create_app
    app = create_app()
    assert app is not None
    # verify blueprints registered via url_map endpoints present
    rules = [str(r.rule) for r in app.url_map.iter_rules()]
    # health and docs should exist
    assert "/" in rules
    assert any(r.startswith("/docs") for r in rules)
