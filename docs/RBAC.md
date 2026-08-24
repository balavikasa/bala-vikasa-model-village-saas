# RBAC and Visibility

| Capability | Admin | PM | PC | DA |
|---|---:|---:|---:|---:|
| Read all clusters | Yes | Yes | No | No |
| Read own PC/DA hierarchy | Yes | Yes | Yes | Own assignments only |
| See disabled master rows | Yes | No | No | No |
| Manage users/master data | Yes | No | No | No |
| Master-data bulk Export/Import | Yes | No | No | No |
| Manage monthly Action Plans | Yes | No | Own DAs/committees | No |
| Export Action Plans | Yes | Yes | Own scope | No |
| Import Action Plans | Yes | No | Own scope | No |
| Submit Attendance/Specials | No | No | No | Own assigned plans |
| View field reports | Global | Global | Own scope | Own scope |
| View map/directory | Global | Global | Own scope | Own scope |
| Soft-delete/restore/audit | Yes | No | No | No |

Authorization is enforced server-side through `app/scoping.py` plus explicit write-capability checks.
Admin is the only role that sees disabled records by default; deleted rows remain excluded from normal
queries and are handled through the recycle-bin workflow.
