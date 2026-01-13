from typing import Any, Dict, Iterable, List, Optional
from .connection import engine, metadata
from . import crud

class Repository:
    """Generic repository for performing CRUD on any reflected table.

    Assumptions:
      - Table already exists in the connected PostgreSQL database.
      - Primary key is first column in table.primary_key for create returning.
    """

    def __init__(self, table_name: str, id_column: str = "id"):
        self.table_name = table_name
        self.id_column = id_column

    def all(self, columns: Optional[Iterable[str]] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        return crud.read_table(engine, metadata, self.table_name, columns=columns, limit=limit, offset=offset)

    def filter(self, where: Dict[str, Any], columns: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        return crud.read_table(engine, metadata, self.table_name, columns=columns, where=where)

    def get(self, id_value: Any) -> Optional[Dict[str, Any]]:
        return crud.get_by_id(engine, metadata, self.table_name, self.id_column, id_value)

    def create(self, values: Dict[str, Any]) -> Any:
        return crud.create_row(engine, metadata, self.table_name, values)

    def update(self, id_value: Any, values: Dict[str, Any]) -> int:
        return crud.update_row(engine, metadata, self.table_name, self.id_column, id_value, values)

    def delete(self, id_value: Any) -> int:
        return crud.delete_row(engine, metadata, self.table_name, self.id_column, id_value)

# Convenience instances (assuming actual table names 'users' and 'tokens')
users_repository = Repository("users", id_column="id")
tokens_repository = Repository("tokens", id_column="id")
