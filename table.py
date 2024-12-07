from sqlalchemy import Column, Integer,JSON,Boolean,ForeignKey,FLOAT
from database import Base

class Warehouse(Base):
    __tablename__ = "Warehouse"

    id = Column(Integer,primary_key=True)
    x_coord = Column(FLOAT,nullable=False)
    y_coord = Column(FLOAT,nullable=False)

class AgentsBigPic(Base):
    __tablename__ = "Agents_bigPic"

    id = Column(Integer,primary_key=True)
    is_checked_in = Column(Boolean,nullable=False,default=False)
    orders = Column(JSON)
    no_of_orders = Column(Integer,nullable=False,default=0)
    total_distance = Column(Integer,nullable=False,default=0)

    warehouse_id = Column(Integer,ForeignKey('Warehouse.id'))

class OrdersBigPic(Base):
    __tablename__ = "Orders_bigPic"

    id = Column(Integer,primary_key=True)
    x_coord = Column(FLOAT,nullable=False)
    y_coord = Column(FLOAT,nullable=False)
    is_delivered = Column(Boolean,nullable=False,default=False)
    
    assigned_agent = Column(Integer,ForeignKey('Agents_bigPic.id'))
    warehouse_id = Column(Integer,ForeignKey('Warehouse.id'))
