"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Security Operations Center (SOC) Project
Complete security monitoring and incident response platform.
"""
import os
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./soc.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    severity = Column(String(20), default="medium")
    source_ip = Column(String(45))
    target = Column(String(512))
    description = Column(Text)
    status = Column(String(50), default="open")
    mitre_tactics = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class IOC(Base):
    __tablename__ = "iocs"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), index=True)
    value = Column(String(1024), index=True)
    threat_level = Column(Float, default=0.0)
    source = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class AlertCreate(BaseModel):
    title: str
    severity: str = "medium"
    source_ip: Optional[str] = None
    target: Optional[str] = None
    description: Optional[str] = None
    mitre_tactics: Optional[str] = None

class AlertResponse(BaseModel):
    id: int
    title: str
    severity: str
    source_ip: Optional[str]
    target: Optional[str]
    description: Optional[str]
    status: str
    mitre_tactics: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="WormGPT SOC Platform", version="2.0.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "soc-platform", "components": ["alerts", "iocs", "threat-intel"]}

@app.post("/alerts", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@app.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    return query.all()

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "alert_id": alert_id, "status": "resolved"}

@app.post("/iocs")
async def register_ioc(type: str, value: str, threat_level: float = 0.0, source: str = "manual"):
    db = SessionLocal()
    try:
        ioc = IOC(type=type, value=value, threat_level=threat_level, source=source)
        db.add(ioc)
        db.commit()
        db.refresh(ioc)
        return {"ok": True, "id": ioc.id}
    finally:
        db.close()

@app.get("/iocs/search")
async def search_iocs(type: Optional[str] = None, value: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(IOC)
        if type:
            query = query.filter(IOC.type == type)
        if value:
            query = query.filter(IOC.value.contains(value))
        return query.all()
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)