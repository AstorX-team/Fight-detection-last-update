# for take iput form user , about LOGIN AND SGHIN UP FORM
# and for validsion
from wsgiref.validate import validator
from click import password_option
from flask_wtf import Form, FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, DateTimeField, BooleanField

from wtforms.validators import DataRequired, EqualTo, Length


class LoginForm(Form):

    email = StringField("email", validators=[Length(
        min=7, max=50), DataRequired(message="Please Fill This Field")])

    password = PasswordField("Password", validators=[
                             DataRequired(message="Please Fill This Field")])


class sign_up_form(Form):
    first_name = StringField(
        'first_name', validators=[DataRequired()]
    )
    last_name = StringField(
        'last_name', validators=[DataRequired()]
    )
    phone = StringField(
        'phone'
    )
    email = StringField(
        'email', validators=[DataRequired()]
    )
    password = PasswordField("password", validators=[

        DataRequired(message="Please Fill This Field"),

        EqualTo(fieldname="confirm", message="Your Passwords Do Not Match")
    ])

    confirm_password = PasswordField("Confirm Password", validators=[
                                     DataRequired(message="Please Fill This Field")])

