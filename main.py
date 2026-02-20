
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, engine

# ============================================================
# IMPORT ALL MODELS (Required for Base.metadata.create_all)
# ============================================================
from user import User, PasswordResetToken
from role import Role
from auth import RefreshToken, AuditLog
from patients import PatientMedicalInfo

from assignments import QuestionnaireAssignment
from patient_dashboard import QuestionnaireInstance, QuestionnaireAnswer
from admin_monitoring import AdminNotification

# ✅ Flow models
from flows import QuestionnaireFlow, FlowNode, FlowNodeOption

# ============================================================
# IMPORT ROUTERS
# ============================================================
import user
import role
from patients import router as patients_router

from assignments import router as assignments_router
from patient_dashboard import router as patient_dashboard_router
from demo_admin import router as demo_admin_router
from admin_monitoring import router as admin_monitoring_router

from flows import router as flows_router

# ============================================================
# APP INITIALIZATION
# ============================================================
app = FastAPI(
    title="Virtual Ward API",
    description="API for Virtual Ward patient monitoring with tree-based questionnaires",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.28.176.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Create all database tables
Base.metadata.create_all(bind=engine)

# ============================================================
# INCLUDE ROUTERS
# ============================================================
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(role.router, prefix="/roles", tags=["Roles"])
app.include_router(patients_router, prefix="/patients", tags=["Patients"])

app.include_router(assignments_router)         # /assignments
app.include_router(patient_dashboard_router)   # /patient
app.include_router(demo_admin_router)          # /demo-admin
app.include_router(admin_monitoring_router)    # /admin

# ✅ Flow management
app.include_router(flows_router)               # /flows

# ============================================================
# ROOT ENDPOINTS
# ============================================================
@app.get("/")
def root():
    return {
        "message": "Virtual Ward API - Tree-Based Questionnaires",
        "version": "2.0.0",
        "docs": "/docs",
        "admin_flows": "/flows/",
        "patient_dashboard": "/patient/dashboard",
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "virtual-ward-api", "version": "2.0.0"}



# venv\Scripts\activate
# uvicorn main:app --reload
