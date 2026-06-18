"""راوتر بلاغات المشاكل — المستخدم يبلّغ والمشرف يراجع.

POST '' متاح لأي مستخدم مسجّل، وقائمة العرض وتحديث الحالة للمشرفين فقط.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.admin import get_admin_user
from ..core.deps import get_current_user
from ..database import get_db
from ..models.issue_report import IssueReport
from ..models.user import User
from ..schemas.issue import IssueIn, IssueOut, IssueStatusIn

router = APIRouter(prefix="/issues", tags=["البلاغات"])


@router.post("", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
def create_issue(
    payload: IssueIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يسجّل بلاغ مشكلة جديد من المستخدم الحالي (يبدأ بحالة 'new')."""
    issue = IssueReport(
        user_id=current_user.id,
        message=payload.message.strip(),
        context=payload.context,
        status="new",
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return IssueOut(
        id=issue.id,
        user_id=issue.user_id,
        username=current_user.username,
        message=issue.message,
        context=issue.context,
        status=issue.status,
        created_at=issue.created_at,
    )


@router.get("", response_model=list[IssueOut])
def list_issues(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """قائمة كل البلاغات (الأحدث أولاً) مع اسم المستخدم المُبلِّغ — للمشرف فقط."""
    rows = db.execute(
        select(IssueReport, User.username)
        .join(User, User.id == IssueReport.user_id)
        .order_by(IssueReport.created_at.desc(), IssueReport.id.desc())
    ).all()
    return [
        IssueOut(
            id=issue.id,
            user_id=issue.user_id,
            username=username,
            message=issue.message,
            context=issue.context,
            status=issue.status,
            created_at=issue.created_at,
        )
        for issue, username in rows
    ]


@router.patch("/{issue_id}", response_model=IssueOut)
def update_issue_status(
    issue_id: int,
    payload: IssueStatusIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """يحدّث حالة بلاغ (new | seen | resolved) — للمشرف فقط."""
    issue = db.get(IssueReport, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="البلاغ غير موجود."
        )
    issue.status = payload.status
    db.commit()
    db.refresh(issue)
    username = db.scalar(select(User.username).where(User.id == issue.user_id))
    return IssueOut(
        id=issue.id,
        user_id=issue.user_id,
        username=username,
        message=issue.message,
        context=issue.context,
        status=issue.status,
        created_at=issue.created_at,
    )
