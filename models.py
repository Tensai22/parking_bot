from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from sqlalchemy import BigInteger

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, nullable=False)
    price_per_hour = Column(Integer, nullable=False)
    available = Column(Boolean, default=True)
    free_spaces = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    parent_spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=True)
    parent_spot = relationship("ParkingSpot", remote_side=[id])
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="parkings")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, nullable=False)
    balance = Column(Integer, default=0)
    car_number = Column(String, nullable=True)

    parkings = relationship("ParkingSpot", back_populates="user")
