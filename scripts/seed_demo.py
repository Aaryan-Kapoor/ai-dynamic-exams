from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.auth import hash_password
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import College, Department, ExamConfig, LectureChunk, LectureMaterial, Role, User
from app.services.lecture_processing import chunk_text
from app.services.vector_index import ensure_chunk_embeddings


COLLEGES_AND_DEPARTMENTS: dict[str, list[str]] = {
    "College of Administration and Economics": [
        "Department of Business Administration",
        "Department of Marketing",
        "Department of Accounting and finance",
        "Department of Health Administration",
        "Department of Tourism Management",
        "Department of Legal Administration",
    ],
    "College of Engineering and Computer Science": [
        "Department of Information Technology",
        "Department of Computer Engineering",
        "Department of Computer Network",
        "Department of Architecture Engineering",
    ],
    "College of Education and Languages": [
        "Department of General Education",
        "Department of Arabic Language and Translation",
        "Department of English Language",
        "Department of French Language",
        "Department of Kurdish Language",
    ],
    "College of Law and International Relations": [
        "Department of Law",
        "Department of Sociology",
        "Department of Diplomacy and International Relations",
    ],
    "College of Nursing": ["Nursing Department"],
    "College of Health Sciences": [
        "Medical Radiology Imaging Department",
        "Medical Laboratory Science Department",
    ],
}


def main() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed colleges/departments
        college_by_name: dict[str, College] = {}
        for college_name in COLLEGES_AND_DEPARTMENTS:
            college = db.scalar(select(College).where(College.name == college_name))
            if not college:
                college = College(name=college_name)
                db.add(college)
                db.commit()
                db.refresh(college)
            college_by_name[college_name] = college

        for college_name, departments in COLLEGES_AND_DEPARTMENTS.items():
            college = college_by_name[college_name]
            for dept_name in departments:
                dept = db.scalar(
                    select(Department)
                    .where(Department.college_id == college.id)
                    .where(Department.name == dept_name)
                )
                if not dept:
                    db.add(Department(college_id=college.id, name=dept_name))
        db.commit()

        # Demo users
        def ensure_user(university_id: str, password: str, role: Role, *, college: College | None = None, grade: int | None = None):
            u = db.scalar(select(User).where(User.university_id == university_id))
            if u:
                return u
            u = User(
                university_id=university_id,
                full_name=university_id,
                password_hash=hash_password(password),
                role=role,
                college_id=college.id if college else None,
                grade_level=grade,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            return u

        eng = college_by_name["College of Engineering and Computer Science"]
        admin = ensure_user("admin", "admin123", Role.system_admin)
        teacher = ensure_user("t1001", "teacher123", Role.teacher, college=eng)
        student = ensure_user("s2001", "student123", Role.student, college=eng, grade=2)

        # Assign departments: teacher in IT + Computer Engineering; student in IT
        it_dept = db.scalar(
            select(Department)
            .where(Department.college_id == eng.id)
            .where(Department.name == "Department of Information Technology")
        )
        ce_dept = db.scalar(
            select(Department)
            .where(Department.college_id == eng.id)
            .where(Department.name == "Department of Computer Engineering")
        )
        if it_dept and it_dept not in teacher.departments:
            teacher.departments.append(it_dept)
        if ce_dept and ce_dept not in teacher.departments:
            teacher.departments.append(ce_dept)
        if it_dept and it_dept not in student.departments:
            student.departments.append(it_dept)
        db.commit()

        # Seed default exam config for IT grade 2
        if it_dept:
            cfg = db.scalar(
                select(ExamConfig)
                .where(ExamConfig.department_id == it_dept.id)
                .where(ExamConfig.grade_level == 2)
            )
            if not cfg:
                cfg = ExamConfig(
                    department_id=it_dept.id,
                    grade_level=2,
                    max_duration_minutes=settings.exam_default_max_duration_minutes,
                    max_attempts=settings.exam_default_max_attempts,
                    max_questions=settings.exam_default_max_questions,
                    stop_consecutive_incorrect=settings.exam_default_stop_consecutive_incorrect,
                    stop_slow_seconds=settings.exam_default_stop_slow_seconds,
                    difficulty_min=settings.exam_default_difficulty_min,
                    difficulty_max=settings.exam_default_difficulty_max,
                    active=True,
                )
                db.add(cfg)
                db.commit()

        # Optional sample lecture so the demo student can start immediately
        if it_dept:
            existing = db.scalar(
                select(LectureMaterial.id)
                .where(LectureMaterial.department_id == it_dept.id)
                .where(LectureMaterial.grade_level == 2)
            )
            if not existing:
                sample_text = """
Introduction to Networking (Grade 2)

1) The OSI model has 7 layers: Physical, Data Link, Network, Transport, Session, Presentation, Application.
2) IP (Internet Protocol) operates at the Network layer and is responsible for routing packets between networks.
3) TCP (Transmission Control Protocol) is connection-oriented and provides reliable, ordered delivery.
4) UDP (User Datagram Protocol) is connectionless and does not guarantee delivery or ordering.
5) A router forwards packets based on destination IP addresses.
6) A switch forwards frames based on MAC addresses at the Data Link layer.
7) DNS translates domain names (like example.com) into IP addresses.
8) HTTP is an application-layer protocol used for web communication.
""".strip()

                material = LectureMaterial(
                    department_id=it_dept.id,
                    grade_level=2,
                    uploaded_by_user_id=teacher.id,
                    original_filename="seed_sample_lecture.txt",
                    stored_path="seed://seed_sample_lecture.txt",
                    file_type="seed",
                    extracted_text=sample_text,
                )
                db.add(material)
                db.commit()
                db.refresh(material)

                chunks = chunk_text(sample_text, chunk_size=settings.chunk_size_chars, overlap=settings.chunk_overlap_chars)
                chunk_rows: list[LectureChunk] = []
                for idx, text in enumerate(chunks):
                    chunk_rows.append(
                        LectureChunk(
                            material_id=material.id,
                            department_id=it_dept.id,
                            grade_level=2,
                            chunk_index=idx,
                            text=text,
                        )
                    )
                db.add_all(chunk_rows)
                db.commit()
                ensure_chunk_embeddings(db, chunk_ids=[c.id for c in chunk_rows], dim=settings.embedding_dim)

        print("Seed complete.")
        print("Demo accounts:")
        print("  admin / admin123")
        print("  t1001 / teacher123")
        print("  s2001 / student123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
