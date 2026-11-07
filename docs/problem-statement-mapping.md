# Problem statement mapping

How each requirement of the AssetFlow problem statement is met. Status: built, partial or planned.

| Requirement | Seller version | Where | Status |
|---|---|---|---|
| Signup creates Employee only | Plain account, no role field | `routers/auth.py`, `schemas/auth.py` | built |
| Admin assigns roles | Owner approves and grants permissions | `routers/team.py`, `core/permissions.py` | built |
| Login, forgot password, session validation | Email and password, token, `/auth/me` | `routers/auth.py` | login built, forgot password planned |
| Dashboard KPI cards, overdue returns | Plus pending payments and open disputes | `routers/dashboard.py` | planned |
| Org setup: departments, categories, directory | Setup tabs | `routers/org_setup.py`, `setup/*` | partial (directory built) |
| Asset registration, tags, QR, search | Stock, materials, capacity slots | `routers/assets.py`, `utils/tags.py`, `utils/qr.py` | planned |
| Lifecycle states | Available, Reserved (hold), Allocated, Under Maintenance, Lost, Retired, Disposed | `core/state_machines.py` | planned |
| Allocation conflict rule, transfer, return | An item cannot be sold twice | `services/allocation_service.py`, `transfer_service.py`, `return_service.py` | planned |
| Booking without overlaps | Production slots and rentals | `services/booking_service.py` | planned |
| Maintenance approval workflow | Rework and disputes | `routers/cases.py`, `services/case_service.py` | planned |
| Audit cycles and discrepancy report | Stock count and payment reconciliation | `routers/audits.py`, `services/audit_service.py` | planned |
| Reports and export | Plus dispute rate and channel performance | `routers/reports.py`, `services/export_service.py` | planned |
| Notifications and activity log | Plus escalations and expiring holds | `services/notification_service.py`, `models/activity_log.py` | log built |
