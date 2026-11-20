from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.models import KRS, KRSDetail, KRSStatus, MataKuliah
from app.services.krs_validators import KRSContext, ValidationResult, build_chain


class KRSError(Exception): pass
class StudentNotFound(KRSError): pass
class CourseNotFound(KRSError): pass
class KRSNotFound(KRSError): pass
class KRSStateConflict(KRSError): pass
class KRSValidationError(KRSError): pass


def _lock_krs(db: Session, nim: str, semester: str) -> KRS:
    # SQLite ignores FOR UPDATE; BEGIN IMMEDIATE serializes writers. MySQL uses row lock.
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    stmt = select(KRS).where(KRS.nim == nim, KRS.semester == semester).with_for_update()
    krs = db.scalar(stmt)
    if krs is None:
        from app.models import CalonMahasiswa
        if db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.nim == nim)) is None:
            db.rollback()
            raise StudentNotFound("NIM tidak ditemukan atau mahasiswa belum di-approve.")
        krs = KRS(nim=nim, semester=semester, status=KRSStatus.draft.value)
        db.add(krs)
        db.flush()
    if krs.status not in (KRSStatus.draft.value, KRSStatus.revision.value):
        db.rollback()
        raise KRSStateConflict("Isi KRS hanya dapat diubah ketika berstatus draft atau revision.")
    return krs


def _context(db: Session, krs: KRS, course: MataKuliah) -> KRSContext:
    existing = list(db.scalars(
        select(MataKuliah).join(KRSDetail, KRSDetail.kode_mk == MataKuliah.kode_mk)
        .where(KRSDetail.krs_id == krs.id).order_by(MataKuliah.kode_mk)
    ).all())
    return KRSContext(krs.nim, krs.semester, existing, course, db, krs.id)


def add_course(db: Session, nim: str, semester: str, kode_mk: str, validator_chain=None) -> KRSDetail:
    try:
        krs = _lock_krs(db, nim, semester)
        course = db.get(MataKuliah, kode_mk)
        if course is None:
            raise CourseNotFound(f"Mata kuliah {kode_mk} tidak ditemukan.")
        result = (validator_chain or build_chain()).validate(_context(db, krs, course))
        if not result.oke:
            raise KRSValidationError(result.message)
        detail = KRSDetail(krs_id=krs.id, kode_mk=kode_mk)
        db.add(detail)
        db.commit()
        db.refresh(detail)
        return detail
    except IntegrityError as exc:
        db.rollback()
        raise KRSValidationError("Mata kuliah sudah tercatat pada KRS ini atau terjadi konflik constraint.") from exc
    except Exception:
        if db.in_transaction(): db.rollback()
        raise


def remove_course(db: Session, nim: str, semester: str, kode_mk: str) -> None:
    try:
        krs = _lock_krs(db, nim, semester)
        detail = db.scalar(select(KRSDetail).where(KRSDetail.krs_id == krs.id, KRSDetail.kode_mk == kode_mk))
        if detail is None:
            raise CourseNotFound("Mata kuliah tersebut tidak ditemukan di KRS.")
        db.delete(detail)
        db.commit()
    except Exception:
        if db.in_transaction(): db.rollback()
        raise


def validate_krs(db: Session, nim: str, semester: str, validator_chain=None) -> list[str]:
    krs = db.scalar(select(KRS).options(joinedload(KRS.details).joinedload(KRSDetail.mata_kuliah)).where(KRS.nim == nim, KRS.semester == semester))
    if krs is None:
        raise KRSNotFound("KRS untuk NIM dan semester tersebut tidak ditemukan.")
    courses = [detail.mata_kuliah for detail in krs.details]
    errors: list[str] = []
    # Full-card validation invokes each check directly so all failures can be collected.
    chain = validator_chain or build_chain()
    validators = []
    current = chain
    while current is not None:
        validators.append(current)
        current = current.next_validator
    for course in courses:
        peers = [item for item in courses if item.kode_mk != course.kode_mk]
        ctx = KRSContext(nim, semester, peers, course, db, krs.id)
        for validator in validators:
            result = validator.check(ctx)
            if not result.oke and result.message not in errors:
                errors.append(result.message)
    # The per-course chain includes duplicate only as an add-time concern; total SKS checked once.
    total = sum(course.sks for course in courses)
    if total > 24:
        errors.insert(0, f"Total SKS {total} melebihi batas maksimal 24 SKS.")
    return errors


class KRSManager:
    """Service facade; semester aktif dan rantai validator diinjeksi saat konstruksi."""
    def __init__(self, db: Session, semester: str, validator_chain=None):
        self.db = db
        self.semester = semester
        self.validator_chain = validator_chain or build_chain()

    def add_course(self, nim: str, kode_mk: str) -> KRSDetail:
        return add_course(self.db, nim, self.semester, kode_mk, self.validator_chain)

    def remove_course(self, nim: str, kode_mk: str) -> None:
        return remove_course(self.db, nim, self.semester, kode_mk)

    def validate_krs(self, nim: str) -> list[str]:
        return validate_krs(self.db, nim, self.semester, self.validator_chain)
