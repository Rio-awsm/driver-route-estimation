HEALTH = "/api/health"
ANY_ORIGIN = "https://anywhere.example"


def test_health(client):
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_any_origin_is_allowed(client):
    response = client.get(HEALTH, headers={"origin": ANY_ORIGIN})
    assert response.headers["access-control-allow-origin"] == "*"


def test_preflight_is_open(client):
    response = client.options(
        HEALTH,
        headers={"origin": ANY_ORIGIN, "access-control-request-method": "POST"},
    )
    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


def test_any_host_is_allowed(client):
    assert client.get(HEALTH, headers={"host": "anything.example"}).status_code == 200


def test_unknown_path_is_404(client):
    assert client.get("/api/nothing").status_code == 404
