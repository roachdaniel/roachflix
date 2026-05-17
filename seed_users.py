"""Run once to create the four family accounts. Set passwords via environment variables."""
import os
from app import create_app
from app.models import db, User

FAMILY = ['Homie', 'Gillian', 'Loren', 'Blythe']

app = create_app()
with app.app_context():
    db.create_all()
    for name in FAMILY:
        if not User.query.filter_by(username=name).first():
            u = User(username=name)
            pw = os.environ.get(f'PASSWORD_{name.upper()}', 'changeme')
            u.set_password(pw)
            db.session.add(u)
            print(f'Created user: {name}')
        else:
            print(f'User already exists: {name}')
    db.session.commit()
    print('Done.')
