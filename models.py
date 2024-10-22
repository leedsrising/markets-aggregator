from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    yes_price = db.Column(db.Float, nullable=False)
    no_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.String(50))
    volume_24h = db.Column(db.String(50))
    close_time = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'description': self.description,
            'yes_contract': {'price': self.yes_price},
            'no_contract': {'price': self.no_price},
            'volume': self.volume,
            'volume_24h': self.volume_24h,
            'close_time': self.close_time
        }