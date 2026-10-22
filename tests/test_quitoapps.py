import pytest
from quitoapps import create_app, db
from quitoapps.config import TestConfig
from quitoapps.models import App, Category, Message, Tag, User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Admin user
        admin = User(username="tester")
        admin.set_password("Secret123456")
        db.session.add(admin)

        # Category and Tag
        cat = Category(slug="herramientas", name_es="Herramientas", name_en="Tools")
        tag = Tag(slug="python", name_es="Python", name_en="Python")
        db.session.add_all([cat, tag])

        # Sample app
        test_app = App(slug="super-tool", status="published", featured=True, visible=True, category=cat, tags=[tag])
        test_app.set_translation("es", "Super Herramienta", "Una herramienta genial", "## Descripción detallada")
        test_app.set_translation("en", "Super Tool", "A cool tool", "## Detailed description")
        test_app.set_link("demo", "https://example.com/demo")
        db.session.add(test_app)
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_root_redirect(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/es/" in res.headers["Location"] or "/en/" in res.headers["Location"]


def test_public_pages_es(client):
    # Index
    res = client.get("/es/")
    assert res.status_code == 200
    assert "Super Herramienta" in res.text

    # Catalog
    res = client.get("/es/apps/")
    assert res.status_code == 200
    assert "Super Herramienta" in res.text

    # Detail
    res = client.get("/es/apps/super-tool/")
    assert res.status_code == 200
    assert "Super Herramienta" in res.text
    assert "Descripción detallada" in res.text

    # About
    res = client.get("/es/about/")
    assert res.status_code == 200

    # Contact
    res = client.get("/es/contact/")
    assert res.status_code == 200


def test_public_pages_en(client):
    res = client.get("/en/")
    assert res.status_code == 200
    assert "Super Tool" in res.text

    res = client.get("/en/apps/super-tool/")
    assert res.status_code == 200
    assert "Super Tool" in res.text
    assert "Detailed description" in res.text


def test_contact_submission(client):
    res = client.post(
        "/es/contact/",
        data={
            "name": "Juan Perez",
            "email": "juan@example.com",
            "message": "Hola! Me encanta el proyecto QuitoApps.",
            "website": "",  # honeypot empty
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    msg = Message.query.filter_by(email="juan@example.com").first()
    assert msg is not None
    assert msg.name == "Juan Perez"
    assert msg.read is False


def test_contact_honeypot(client):
    res = client.post(
        "/es/contact/",
        data={
            "name": "Bot",
            "email": "bot@spam.com",
            "message": "Buy crypto now!",
            "website": "http://spam.com",  # honeypot filled
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    # No se guarda en BD
    assert Message.query.filter_by(email="bot@spam.com").first() is None


def test_seo_endpoints(client):
    # robots.txt
    res = client.get("/robots.txt")
    assert res.status_code == 200
    assert "User-agent: *" in res.text

    # sitemap.xml
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    assert "super-tool" in res.text

    # feed.xml
    res = client.get("/es/feed.xml")
    assert res.status_code == 200
    assert "Super Herramienta" in res.text


def test_admin_auth_and_dashboard(client):
    # Protegido sin login
    res = client.get("/admin/")
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]

    # Login incorrecto
    res = client.post("/admin/login", data={"username": "tester", "password": "wrongpassword"})
    assert res.status_code == 200
    assert "incorrectos" in res.text

    # Login correcto
    res = client.post("/admin/login", data={"username": "tester", "password": "Secret123456"}, follow_redirects=True)
    assert res.status_code == 200
    assert "Panel" in res.text

    # Apps admin
    res = client.get("/admin/apps")
    assert res.status_code == 200
    assert "Super Herramienta" in res.text

    # Logout
    res = client.post("/admin/logout", follow_redirects=True)
    assert res.status_code == 200
    assert "Iniciar sesión" in res.text
