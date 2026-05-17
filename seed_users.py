"""Run once to create the four family accounts."""
from app import create_app
from app.models import db, User

FAMILY = ['Father', 'Mother', 'Loren', 'Blythe']

app = create_app()
with app.app_context():
    db.create_all()
    for name in FAMILY:
        if not User.query.filter_by(username=name).first():
            u = User(username=name)
            u.set_password('unused')
            db.session.add(u)
            print(f'Created user: {name}')
        else:
            print(f'Already exists: {name}')
    db.session.commit()
    print('Done.')
