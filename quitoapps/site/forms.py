from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import EmailField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    name = StringField(_l("Name"), validators=[DataRequired(), Length(max=120)])
    email = EmailField(_l("Email"), validators=[DataRequired(), Email(check_deliverability=False), Length(max=200)])
    message = TextAreaField(_l("Message"), validators=[DataRequired(), Length(min=10, max=5000)])
    # Honeypot: oculto con CSS; las personas no lo ven ni lo rellenan.
    website = StringField("Website")
