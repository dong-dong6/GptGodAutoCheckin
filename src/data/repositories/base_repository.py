"""
Repository基类
提供统一的数据访问接口
"""
import logging
from typing import Optional, List, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
from ..database import get_db


T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Repository基类"""

    def __init__(self, table_name: str):
        """
        初始化Repository

        Args:
            table_name: 表名
        """
        self.table_name = table_name
        self.db = get_db()

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False
    ) -> Optional[Any]:
        """
        执行SQL查询

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否返回单条记录
            fetch_all: 是否返回所有记录
            commit: 是否提交事务

        Returns:
            查询结果
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)

            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()

            if commit:
                conn.commit()

            return result

        except Exception as e:
            logging.error(f"执行查询失败: {query}, 错误: {e}")
            if commit:
                conn.rollback()
            raise

    def find_by_id(self, id_value: int) -> Optional[Dict[str, Any]]:
        """
        根据ID查找记录

        Args:
            id_value: ID值

        Returns:
            记录字典，不存在则返回None
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        result = self.execute_query(query, (id_value,), fetch_one=True)

        if result:
            return self._row_to_dict(result)
        return None

    def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查找所有记录

        Args:
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            记录列表
        """
        query = f"SELECT * FROM {self.table_name}"

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        results = self.execute_query(query, fetch_all=True)

        return [self._row_to_dict(row) for row in (results or [])]

    def count(self, where_clause: str = "", params: tuple = ()) -> int:
        """
        统计记录数量

        Args:
            where_clause: WHERE子句（不包含WHERE关键字）
            params: 查询参数

        Returns:
            记录数量
        """
        query = f"SELECT COUNT(*) FROM {self.table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"

        result = self.execute_query(query, params, fetch_one=True)
        return result[0] if result else 0

    def delete_by_id(self, id_value: int) -> bool:
        """
        根据ID删除记录

        Args:
            id_value: ID值

        Returns:
            是否删除成功
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = ?"
            self.execute_query(query, (id_value,), commit=True)
            logging.info(f"已删除记录: {self.table_name}.id={id_value}")
            return True
        except Exception as e:
            logging.error(f"删除记录失败: {e}")
            return False

    def execute_raw(
        self,
        query: str,
        params: tuple = (),
        fetch: bool = False
    ) -> Optional[Any]:
        """
        执行原始SQL

        Args:
            query: SQL语句
            params: 参数
            fetch: 是否返回结果

        Returns:
            查询结果
        """
        return self.execute_query(
            query,
            params,
            fetch_all=fetch,
            commit=not fetch
        )

    @abstractmethod
    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        """
        将数据库行转换为字典（需要子类实现）

        Args:
            row: 数据库行

        Returns:
            字典
        """
        pass

    def _dict_to_row(self, data: Dict[str, Any]) -> tuple:
        """
        将字典转换为数据库行（可选实现）

        Args:
            data: 数据字典

        Returns:
            元组
        """
        raise NotImplementedError("子类需要实现此方法")


class CRUDRepository(BaseRepository[T], ABC):
    """
    CRUD Repository基类
    提供完整的增删改查操作
    """

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Optional[int]:
        """
        创建记录

        Args:
            data: 数据字典

        Returns:
            新记录的ID，失败返回None
        """
        pass

    @abstractmethod
    def update(self, id_value: int, data: Dict[str, Any]) -> bool:
        """
        更新记录

        Args:
            id_value: 记录ID
            data: 更新数据

        Returns:
            是否更新成功
        """
        pass

    def delete(self, id_value: int) -> bool:
        """
        删除记录（继承自BaseRepository）

        Args:
            id_value: 记录ID

        Returns:
            是否删除成功
        """
        return self.delete_by_id(id_value)

    def read(self, id_value: int) -> Optional[Dict[str, Any]]:
        """
        读取记录（继承自BaseRepository）

        Args:
            id_value: 记录ID

        Returns:
            记录字典
        """
        return self.find_by_id(id_value)


# 示例用法
if __name__ == '__main__':
    class UserRepository(CRUDRepository):
        """示例用户Repository"""

        def __init__(self):
            super().__init__('users')

        def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
            return {
                'id': row[0],
                'email': row[1],
                'name': row[2],
                'created_at': row[3]
            }

        def create(self, data: Dict[str, Any]) -> Optional[int]:
            query = "INSERT INTO users (email, name) VALUES (?, ?)"
            try:
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, (data['email'], data['name']))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logging.error(f"创建用户失败: {e}")
                return None

        def update(self, id_value: int, data: Dict[str, Any]) -> bool:
            query = "UPDATE users SET email = ?, name = ? WHERE id = ?"
            try:
                self.execute_query(
                    query,
                    (data['email'], data['name'], id_value),
                    commit=True
                )
                return True
            except Exception as e:
                logging.error(f"更新用户失败: {e}")
                return False

    print("Repository基类创建成功")
