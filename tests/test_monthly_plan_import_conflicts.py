from __future__ import annotations

from datetime import UTC, datetime

from app.extensions import db
from app.models import (
    DA,
    PC,
    ActionPlan,
    ActionPlanType,
    Cluster,
    Committee,
    Role,
    User,
    Village,
)
from app.services.monthly_plans import (
    EXPORT_SHEET,
    build_export_workbook,
    confirm_import,
    current_month,
    stage_import,
)


def test_import_restores_soft_deleted_committee_month_without_duplicate(
    app,
    tmp_path,
):
    with app.app_context():
        admin = User(
            email="import-admin@example.org",
            role=Role.ADMIN,
            display_name="Import Admin",
        )
        admin.set_password("StrongPass123!")

        pc = PC(
            full_name="Test PC",
            cluster=Cluster.CSRB,
        )

        da = DA(
            full_name="Test DA",
            pc=pc,
        )

        village = Village(
            name="Test Village",
            da=da,
        )

        committee = Committee(
            name="Environment",
            village=village,
        )

        selected_month = current_month()

        archived_plan = ActionPlan(
            committee=committee,
            title=committee.name,
            description=None,
            plan_month=selected_month,
            plan_type=ActionPlanType.ATTENDANCE,
            assigned_date=None,
            assigned_by_user_id=None,
            notes="Archived plan",
            is_enabled=False,
            is_deleted=True,
            deleted_at=datetime.now(UTC),
        )

        db.session.add_all(
            [
                admin,
                pc,
                da,
                village,
                committee,
                archived_plan,
            ]
        )
        db.session.commit()

        archived_plan_id = archived_plan.id
        committee_id = committee.id

        workbook = build_export_workbook(
            admin,
            selected_month,
        )

        sheet = workbook[EXPORT_SHEET]

        headers = {
            cell.value: cell.column
            for cell in sheet[1]
        }

        target_row = None

        for row_number in range(2, sheet.max_row + 1):
            if (
                sheet.cell(
                    row_number,
                    headers["Committee ID"],
                ).value
                == committee_id
            ):
                target_row = row_number
                break

        assert target_row is not None

        # A soft-deleted plan should appear to the user as an available
        # monthly slot, so the exported active sheet has no active Plan ID.
        assert (
            sheet.cell(
                target_row,
                headers["Plan ID"],
            ).value
            in {None, ""}
        )

        sheet.cell(
            target_row,
            headers["Type"],
        ).value = "Attendance"

        sheet.cell(
            target_row,
            headers["Notes"],
        ).value = "Restored by import"

        workbook_path = (
            tmp_path
            / "action_plan_soft_delete_restore.xlsx"
        )

        workbook.save(workbook_path)

        token, preview = stage_import(
            workbook_path,
            admin,
            selected_month,
        )

        assert preview["has_errors"] is False
        assert preview["counts"]["New"] == 1
        assert preview["counts"]["Error"] == 0

        matching_preview_rows = [
            row
            for row in preview["rows"]
            if row["committee_id"] == committee_id
        ]

        assert len(matching_preview_rows) == 1

        preview_row = matching_preview_rows[0]

        assert preview_row["action"] == "New"

        # The important regression assertion:
        # even though the UI classifies the archived slot as New,
        # Confirm Import must reuse/restore the existing database row
        # instead of INSERTing another committee/month row.
        result = confirm_import(
            token,
            admin,
            selected_month,
        )

        assert result["created"] == 1
        assert result["updated"] == 0

        plans = list(
            db.session.scalars(
                db.select(ActionPlan).where(
                    ActionPlan.committee_id
                    == committee_id,
                    ActionPlan.plan_month
                    == selected_month,
                )
            )
        )

        assert len(plans) == 1

        restored = plans[0]

        assert restored.id == archived_plan_id
        assert restored.is_deleted is False
        assert restored.is_enabled is True
        assert restored.deleted_at is None
        assert restored.plan_type == ActionPlanType.ATTENDANCE
        assert restored.notes == "Restored by import"