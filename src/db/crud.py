from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.test_models import ClassProfile, Course, Enrollment, Student


class ClassProfileEnum(str, Enum):
    SCIENCE = "science"
    ARTS = "arts"
    COMMERCIAL = "commercial"


class StudentSchema(BaseModel):
    matriculation_number: str
    firstname: str
    lastname: str
    age: int
    registered_at: str = Field(default_factory=lambda _: datetime.now().isoformat())
    class_profile: ClassProfileEnum | None = None
    courses: list["CourseSchema"] = Field(default_factory=list)


class CourseSchema(BaseModel):
    name: "CourseNameEnum"
    units: int = Field(ge=1, le=3)
    registered_at: str = Field(default_factory=lambda _: datetime.now().isoformat())
    students: list[StudentSchema] = Field(default_factory=list)


class EnrollmentSchema(BaseModel):
    student_id: int
    course_id: int
    grade: float | None = None
    registered_at: str = Field(default_factory=lambda _: datetime.now().isoformat())
    student: StudentSchema | None = None
    course: CourseSchema | None = None


class ClassProfileSchema(BaseModel):
    profile: ClassProfileEnum
    registered_at: str = Field(default_factory=lambda _: datetime.now().isoformat())


class CourseNameEnum(str, Enum):
    ENGLISH_LANGUAGE = "english language"
    MATHEMATICS = "mathematics"
    CIVIC_EDUCATION = "civic education"
    BIOLOGY = "biology"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    LITERATURE_IN_ENGLISH = "literature in english"
    GOVERNMENT = "government"
    ECONOMICS = "economics"
    COMMERCE = "commerce"


# =========================================================
# ==================== CRUD Operations ====================
# =========================================================
def get_class_profile_by_name(
    db: Session, name: ClassProfileEnum | str
) -> ClassProfile:
    """Get class profile by name."""
    return db.query(ClassProfile).filter(ClassProfile.profile == name).first()


def get_course_name(db: Session, name: CourseNameEnum | str) -> Course:
    """Get course by name."""
    return db.query(Course).filter(Course.name == name).first()


def get_course_by_id(db: Session, course_id: int) -> Course:
    """Get course by ID."""
    return db.query(Course).filter(Course.id == course_id).first()


def get_student_by_matric_no(db: Session, matric_no: str) -> Student:
    """Get student by matriculation number."""
    return db.query(Student).filter(Student.matric_no == matric_no).first()


def get_student_by_id(db: Session, student_id: int) -> Student:
    """Get student by ID."""
    return db.query(Student).filter(Student.id == student_id).first()


def get_class_profile_by_id(db: Session, class_profile_id: int) -> ClassProfile:
    """Get class profile by ID."""
    return db.query(ClassProfile).filter(ClassProfile.id == class_profile_id).first()


def create_student(db: Session, student: StudentSchema) -> Student:
    """Create a new student in the database."""
    # Check if student already exists
    existing_student = get_student_by_matric_no(
        db=db, matric_no=student.matriculation_number
    )
    if existing_student:
        raise ValueError(
            "Student with the same firstname, lastname and matriculation number already exists."
        )

    db_student = Student(
        firstname=student.firstname,
        lastname=student.lastname,
        age=student.age,
        matriculation_number=student.matriculation_number,
        class_profile=student.class_profile.value if student.class_profile else None,
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def create_class_profiles(db: Session) -> None:
    """Create default class profiles if they do not exist."""
    arts_name = ClassProfileEnum.ARTS.value
    commercial_name = ClassProfileEnum.COMMERCIAL.value
    science_name = ClassProfileEnum.SCIENCE.value

    if (
        not get_class_profile_by_name(db, name=arts_name)
        and not get_class_profile_by_name(db, name=commercial_name)
        and not get_class_profile_by_name(db, name=science_name)
    ):
        return  # Profiles already exist

    # Else, create them
    arts = ClassProfile(profile=ClassProfileEnum.ARTS.value)
    commercial = ClassProfile(profile=ClassProfileEnum.COMMERCIAL.value)
    science = ClassProfile(profile=ClassProfileEnum.SCIENCE.value)
    for profile in [arts, commercial, science]:
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return


def create_course_by_name(db: Session, course: CourseSchema) -> Course:
    """Create a new course in the database."""
    if not get_course_name(db, name=course.name):
        course_name = Course(
            name=course.name, units=course.units, registered_at=course.registered_at
        )
        db.add(course_name)
        db.commit()
        db.refresh(course_name)
        return course_name

    raise ValueError("Course with the same name already exists.")


def enroll_student_into_course(db: Session, course_id: int, matric_no: str):
    student = get_student_by_matric_no(db, matric_no)
    course = get_course_by_id(db, course_id)
    if not student or not course:
        raise ValueError("not found")

    existing = (
        db.query(Enrollment)
        .filter_by(student_id=student.id, course_id=course.id)
        .first()
    )
    if existing:
        return existing

    enrollment = Enrollment(student_id=student.id, course_id=course.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def unenroll_student_from_course(db: Session, course_id: int, matric_no: str) -> Course:
    """Remove a student from a course's student list.

    If the student is enrolled, remove them and commit. Returns the Course.
    """
    course = get_course_by_id(db=db, course_id=course_id)
    if not course:
        raise ValueError("Course not found")

    student = get_student_by_matric_no(db=db, matric_no=matric_no)
    if not student:
        raise ValueError("Student not found")

    if student in getattr(course, "students", []):
        course.students.remove(student)
        db.add(course)
        db.commit()
        db.refresh(course)

    return course


def enroll_class_profile(
    db: Session, class_profile_id: int, matric_no: str
) -> ClassProfile:
    """Enroll an existing student into an existing class profile."""
    class_profile = get_class_profile_by_id(db=db, class_profile_id=class_profile_id)
    if not class_profile:
        raise ValueError("Class Profile not found")

    student = get_student_by_matric_no(db=db, matric_no=matric_no)
    if not student:
        raise ValueError("Student not found")

    # Verify that the student has not been enrolled
    if student in getattr(class_profile, "students", []):
        return class_profile

    class_profile.students.append(student)
    db.add(class_profile)
    db.commit()
    db.refresh(class_profile)

    return class_profile


def unenroll_class_profile(
    db: Session, class_profile_id: int, matric_no: str
) -> ClassProfile:
    """Remove a student from a class profile's student list.

    If the student is enrolled, remove them and commit. Returns the ClassProfile.
    """
    class_profile = get_class_profile_by_id(db=db, class_profile_id=class_profile_id)
    if not class_profile:
        raise ValueError("Class Profile not found")

    student = get_student_by_matric_no(db=db, matric_no=matric_no)
    if not student:
        raise ValueError("Student not found")

    if student in getattr(class_profile, "students", []):
        class_profile.students.remove(student)
        db.add(class_profile)
        db.commit()
        db.refresh(class_profile)

    return class_profile
