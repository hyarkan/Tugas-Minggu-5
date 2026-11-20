from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KRS, KRSDetail, MataKuliah
from app.schemas.krs import AddCourseRequest, KRSDetailResponse, KRSResponse, KRSValidationResponse
from app.services.krs_service import (add_course, remove_course, validate_krs,
    StudentNotFound, CourseNotFound, KRSNotFound, KRSStateConflict, KRSValidationError, KRSManager)

router = APIRouter(prefix="/api/krs", tags=["KRS"])


def _http_error(exc: Exception):
    if isinstance(exc, StudentNotFound): code = 404
    elif isinstance(exc, (CourseNotFound, KRSNotFound)): code = 404
    elif isinstance(exc, KRSStateConflict): code = 409
    elif isinstance(exc, KRSValidationError): code = 400
    else: code = 400
    raise HTTPException(status_code=code, detail=str(exc))


@router.post("/{nim}/{semester}/courses", response_model=KRSDetailResponse, status_code=201,
             summary="Menambahkan mata kuliah ke KRS")
def add_course_endpoint(nim: str, semester: str, payload: AddCourseRequest, db: Session = Depends(get_db)):
    if len(semester) != 5 or not semester[:4].isdigit() or semester[4] not in "12":
        raise HTTPException(status_code=422, detail="Format semester harus YYYY1 (ganjil) atau YYYY2 (genap).")
    try:
        return KRSManager(db, semester).add_course(nim, payload.kode_mk)
    except Exception as exc:
        _http_error(exc)


@router.delete("/{nim}/{semester}/courses/{kode_mk}", status_code=204,
               summary="Menghapus mata kuliah dari KRS")
def remove_course_endpoint(nim: str, semester: str, kode_mk: str, db: Session = Depends(get_db)):
    try:
        KRSManager(db, semester).remove_course(nim, kode_mk)
        return None
    except Exception as exc:
        _http_error(exc)


@router.get("/{nim}/{semester}/validate", response_model=KRSValidationResponse,
            summary="Memvalidasi seluruh isi KRS")
def validate_krs_endpoint(nim: str, semester: str, db: Session = Depends(get_db)):
    try:
        errors = KRSManager(db, semester).validate_krs(nim)
        return {"valid": not errors, "errors": errors}
    except Exception as exc:
        _http_error(exc)


@router.get("/{nim}/{semester}", response_model=KRSResponse, summary="Melihat KRS mahasiswa")
def get_krs_endpoint(nim: str, semester: str, db: Session = Depends(get_db)):
    krs = db.scalar(select(KRS).where(KRS.nim == nim, KRS.semester == semester))
    if krs is None:
        raise HTTPException(status_code=404, detail="KRS tidak ditemukan.")
    rows = db.execute(select(MataKuliah.nama, MataKuliah.sks)
        .join(KRSDetail, KRSDetail.kode_mk == MataKuliah.kode_mk)
        .where(KRSDetail.krs_id == krs.id)).all()
    return {"id": krs.id, "nim": krs.nim, "semester": krs.semester,
            "status": krs.status, "total_sks": sum(row.sks for row in rows),
            "mata_kuliah": [row.nama for row in rows]}
