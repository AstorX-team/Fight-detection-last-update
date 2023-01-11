from flask import redirect, session, url_for


def check_login(login):
        if login not in session:
            return redirect(url_for('login'))