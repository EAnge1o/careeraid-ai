from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import db


class Student(db.Model):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    major: Mapped[Optional[str]] = mapped_column(nullable=True)

    resume_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_parsed_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality_test_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_version: Mapped[int] = mapped_column(default=1, nullable=False)  # 数据版本号，用于缓存键

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    def increment_version(self):
        """增加数据版本号"""
        self.data_version += 1
        db.session.commit()

    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "major": self.major,
            "resume_raw_text": self.resume_raw_text,
            "resume_parsed_json": self.resume_parsed_json,
            "personality_test_json": self.personality_test_json,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict_admin(self) -> dict[str, Any]:
        """管理员视图的字典表示，包含更多信息"""
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "major": self.major,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Job(db.Model):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(nullable=True)
    requirements_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 企业岗位数据字段：职位名称、工作地址、薪资范围、公司全称、所属行业、人员规模、企业性质、职位编码、职位描述、公司简介
    work_address: Mapped[Optional[str]] = mapped_column(nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    company_scale: Mapped[Optional[str]] = mapped_column(nullable=True)
    company_nature: Mapped[Optional[str]] = mapped_column(nullable=True)
    job_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    job_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "industry": self.industry,
            "salary": self.salary,
            "requirements_text": self.requirements_text,
            "job_profile_json": self.job_profile_json,
            "work_address": self.work_address,
            "company_name": self.company_name,
            "company_scale": self.company_scale,
            "company_nature": self.company_nature,
            "job_code": self.job_code,
            "job_desc": self.job_desc,
            "company_intro": self.company_intro,
            "created_at": (self.created_at or datetime.utcnow()).isoformat(),
            "updated_at": (self.updated_at or datetime.utcnow()).isoformat(),
        }


class MatchResult(db.Model):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    dimension_scores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gap_analysis_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="match_results")
    job: Mapped["Job"] = relationship(back_populates="match_results")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "score": self.score,
            "dimension_scores_json": self.dimension_scores_json,
            "gap_analysis_json": self.gap_analysis_json,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat(),
        }


class Report(db.Model):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="reports")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)  # user | ai | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class Feedback(db.Model):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)  # 1-5星
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_type: Mapped[str] = mapped_column(nullable=False)  # match | recommendation | report
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    student: Mapped["Student"] = relationship()
    job: Mapped["Job"] = relationship()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "job_id": self.job_id,
            "rating": self.rating,
            "comment": self.comment,
            "feedback_type": self.feedback_type,
            "created_at": self.created_at.isoformat(),
        }