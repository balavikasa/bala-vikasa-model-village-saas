# Route inventory

Generated statically from Flask decorators. Dash owns its mounted routes under `/dash/`.

| Method | Route | Handler | Source |
|---|---|---|---|
| GET | `/` | `home` | `app/pages.py` |
| GET | `/admin` | `admin` | `app/pages.py` |
| POST | `/api/v1/action-plans` | `create_action_plan_route` | `app/api.py` |
| GET, POST | `/api/v1/admin/<slug>` | `collection` | `app/admin_api.py` |
| DELETE | `/api/v1/admin/<slug>/<int:record_id>` | `delete` | `app/admin_api.py` |
| PATCH | `/api/v1/admin/<slug>/<int:record_id>` | `update` | `app/admin_api.py` |
| POST | `/api/v1/admin/<slug>/<int:record_id>/toggle` | `toggle` | `app/admin_api.py` |
| GET | `/api/v1/admin/audit-logs/items` | `audit_logs` | `app/admin_api.py` |
| POST | `/api/v1/admin/recycle-bin/<int:item_id>/restore` | `restore` | `app/admin_api.py` |
| GET | `/api/v1/admin/recycle-bin/items` | `recycle_items` | `app/admin_api.py` |
| GET | `/api/v1/admin/resources` | `resources` | `app/admin_api.py` |
| GET | `/api/v1/attendance` | `list_attendance` | `app/api.py` |
| POST | `/api/v1/attendance` | `submit_attendance` | `app/api.py` |
| GET | `/api/v1/auth/csrf` | `csrf_token` | `app/api.py` |
| GET | `/api/v1/committees/<int:committee_id>/action-plans` | `committee_action_plans` | `app/api.py` |
| GET | `/api/v1/directory` | `directory_data` | `app/api.py` |
| GET | `/api/v1/me` | `me` | `app/api.py` |
| GET | `/api/v1/monitoring/map` | `monitoring_map` | `app/api.py` |
| GET | `/api/v1/monitoring/series` | `monitoring_series_route` | `app/api.py` |
| GET | `/api/v1/monitoring/summary` | `monitoring_summary` | `app/api.py` |
| GET | `/api/v1/photos/<entry_type>/<int:entry_id>` | `photo` | `app/api.py` |
| GET | `/api/v1/specials` | `list_specials` | `app/api.py` |
| POST | `/api/v1/specials` | `submit_specials` | `app/api.py` |
| GET | `/api/v1/villages` | `villages` | `app/api.py` |
| GET | `/api/v1/villages/<int:village_id>/committees` | `village_committees` | `app/api.py` |
| GET | `/dash/` | `dash_missing` | `app/dashboards.py` |
| GET | `/directory` | `directory` | `app/pages.py` |
| GET | `/field/attendance` | `attendance` | `app/pages.py` |
| GET | `/field/specials` | `specials` | `app/pages.py` |
| GET, POST | `/login` | `login` | `app/auth.py` |
| POST | `/logout` | `logout` | `app/auth.py` |
| GET | `/manifest.json` | `manifest` | `app/pages.py` |
| GET | `/monitoring` | `monitoring` | `app/pages.py` |
| GET | `/offline` | `offline` | `app/pages.py` |
| GET | `/overview` | `overview` | `app/pages.py` |
| GET | `/sw.js` | `service_worker` | `app/pages.py` |
