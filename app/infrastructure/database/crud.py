from typing import Any, Dict, Iterable, List, Optional
from sqlalchemy import Table, select, insert, update as sa_update, delete as sa_delete, MetaData
from sqlalchemy.engine import Engine


def _reflect_table(table_name: str, metadata: MetaData, engine: Engine) -> Table:
    return Table(table_name, metadata, autoload_with=engine)


def read_table(
    engine: Engine,
    metadata: MetaData,
    table_name: str,
    columns: Optional[Iterable[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Read rows from a table.

    - columns: iterable of column names to include; default selects all.
    - where: dict of column->value equality filters.
    - limit/offset for pagination.
    """
    table = _reflect_table(table_name, metadata, engine)
    if columns:
        cols = [table.c[col] for col in columns]
    else:
        cols = [table]

    stmt = select(*cols)

    if where:
        for k, v in where.items():
            stmt = stmt.where(getattr(table.c, k) == v)

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    with engine.connect() as conn:
        result = conn.execute(stmt)
        rows = [dict(row._mapping) for row in result.fetchall()]
    return rows


def get_by_id(
    engine: Engine,
    metadata: MetaData,
    table_name: str,
    id_column: str,
    id_value: Any,
) -> Optional[Dict[str, Any]]:
    table = _reflect_table(table_name, metadata, engine)
    stmt = select(table).where(getattr(table.c, id_column) == id_value).limit(1)
    with engine.connect() as conn:
        result = conn.execute(stmt).first()
        return dict(result._mapping) if result else None


def create_row(
    engine: Engine,
    metadata: MetaData,
    table_name: str,
    values: Dict[str, Any],
) -> Any:
    table = _reflect_table(table_name, metadata, engine)
    stmt = insert(table).values(**values).returning(table.primary_key.columns.values()[0])
    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.scalar()  # returns inserted primary key if supported


def update_row(
    engine: Engine,
    metadata: MetaData,
    table_name: str,
    id_column: str,
    id_value: Any,
    values: Dict[str, Any],
) -> int:
    table = _reflect_table(table_name, metadata, engine)
    stmt = sa_update(table).where(getattr(table.c, id_column) == id_value).values(**values)
    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.rowcount or 0


def delete_row(
    engine: Engine,
    metadata: MetaData,
    table_name: str,
    id_column: str,
    id_value: Any,
) -> int:
    table = _reflect_table(table_name, metadata, engine)
    stmt = sa_delete(table).where(getattr(table.c, id_column) == id_value)
    with engine.begin() as conn:
        result = conn.execute(stmt)
        return result.rowcount or 0
