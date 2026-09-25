"""Blog author CRUD — kept out of BlogService LOC budget."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.website_content_models import BlogAuthor, BlogPost

BLOG_AUTHOR_ID_MAX = 64
BLOG_AUTHOR_NAME_MAX = 256
BLOG_AUTHOR_ROLE_MAX = 256
BLOG_AUTHOR_BIO_MAX = 4000


class BlogAuthorMixin:
    """Author registry methods mixed into BlogService."""

    def list_authors(self, db: Session) -> list[BlogAuthor]:
        return db.query(BlogAuthor).order_by(BlogAuthor.name.asc()).all()

    def get_author(self, db: Session, author_id: str) -> BlogAuthor | None:
        return db.query(BlogAuthor).filter(BlogAuthor.id == author_id.strip().lower()).first()

    def create_author(
        self,
        db: Session,
        *,
        author_id: str,
        name: str,
        role: str = "",
        bio: str = "",
    ) -> BlogAuthor:
        aid = self._validate_author_id(author_id)  # type: ignore[attr-defined]
        if self.get_author(db, aid):
            raise ValueError("blog_author_exists")
        clean_name = name.strip()
        if not clean_name or len(clean_name) > BLOG_AUTHOR_NAME_MAX:
            raise ValueError("blog_invalid_author_name")
        clean_role = (role or "").strip()
        if len(clean_role) > BLOG_AUTHOR_ROLE_MAX:
            raise ValueError("blog_invalid_author_role")
        clean_bio = (bio or "").strip()
        if len(clean_bio) > BLOG_AUTHOR_BIO_MAX:
            raise ValueError("blog_invalid_author_bio")
        record = BlogAuthor(id=aid, name=clean_name, role=clean_role, bio=clean_bio)
        db.add(record)
        self._commit(db)  # type: ignore[attr-defined]
        db.refresh(record)
        return record

    def update_author(
        self,
        db: Session,
        author_id: str,
        *,
        name: str | None = None,
        role: str | None = None,
        bio: str | None = None,
    ) -> BlogAuthor:
        record = self.get_author(db, author_id)
        if not record:
            raise LookupError("blog_author_not_found")
        if name is not None:
            clean_name = name.strip()
            if not clean_name or len(clean_name) > BLOG_AUTHOR_NAME_MAX:
                raise ValueError("blog_invalid_author_name")
            record.name = clean_name
        if role is not None:
            clean_role = role.strip()
            if len(clean_role) > BLOG_AUTHOR_ROLE_MAX:
                raise ValueError("blog_invalid_author_role")
            record.role = clean_role
        if bio is not None:
            clean_bio = bio.strip()
            if len(clean_bio) > BLOG_AUTHOR_BIO_MAX:
                raise ValueError("blog_invalid_author_bio")
            record.bio = clean_bio
        self._commit(db)  # type: ignore[attr-defined]
        db.refresh(record)
        return record

    def delete_author(self, db: Session, author_id: str) -> None:
        record = self.get_author(db, author_id)
        if not record:
            raise LookupError("blog_author_not_found")
        in_use = (
            db.query(BlogPost.id).filter(BlogPost.author_id == record.id).limit(1).first()
        )
        if in_use:
            raise ValueError("blog_author_in_use")
        db.delete(record)
        self._commit(db)  # type: ignore[attr-defined]

    def serialize_author(self, record: BlogAuthor) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "role": record.role or "",
            "bio": record.bio or "",
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
