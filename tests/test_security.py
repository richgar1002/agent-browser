import security


def test_validate_url_blocks_localhost():
    valid, error = security.RequestValidator.validate_url("http://localhost:8000")
    assert valid is False
    assert "Localhost" in error


def test_validate_url_blocks_private_ip():
    original = security.SecurityConfig.ALLOW_PRIVATE_NETWORK
    security.SecurityConfig.ALLOW_PRIVATE_NETWORK = False
    try:
        valid, error = security.RequestValidator.validate_url("http://192.168.1.10")
        assert valid is False
        assert "Private/internal" in error
    finally:
        security.SecurityConfig.ALLOW_PRIVATE_NETWORK = original


def test_validate_url_allows_private_ip_when_enabled():
    original = security.SecurityConfig.ALLOW_PRIVATE_NETWORK
    security.SecurityConfig.ALLOW_PRIVATE_NETWORK = True
    try:
        valid, error = security.RequestValidator.validate_url("http://192.168.1.10")
        assert valid is True
        assert error is None
    finally:
        security.SecurityConfig.ALLOW_PRIVATE_NETWORK = original

