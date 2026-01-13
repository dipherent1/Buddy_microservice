"""Legacy db module.

Re-exports new database utilities from `app.infrastructure.database` so existing
imports like `from app.infrastructure.db import ...` continue working.
"""

from app.infrastructure.database import (
	engine,
	SessionLocal,
	get_session,
	metadata,
	read_table,
	get_by_id,
	create_row,
	update_row,
	delete_row,
	Repository,
)

__all__ = [
	"engine",
	"SessionLocal",
	"get_session",
	"metadata",
	"read_table",
	"get_by_id",
	"create_row",
	"update_row",
	"delete_row",
	"Repository",
]
