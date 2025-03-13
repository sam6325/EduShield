import mysql.connector
from typing import List, Dict


class DatabaseManager:
    def __init__(
        self, host: str = "10.167.214.47", user: str = "admin", password: str = "dv107"
    ):
        """初始化資料庫連接"""
        self.db_connection = mysql.connector.connect(
            host=host, user=user, password=password
        )
        self.db_cursor = self.db_connection.cursor()

    def check_category_exists(self, category: str) -> bool:
        """檢查資料庫中是否已經存在該資料庫"""
        query = (
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s"
        )
        # 修正：確保 category 是元組
        category_param = (category,) if isinstance(category, str) else category
        self.db_cursor.execute(query, (category_param))
        result = self.db_cursor.fetchone()
        return result is not None

    def create_category_database(self, category: str):
        """創建新的資料庫"""
        query = f"CREATE DATABASE {category}"
        self.db_cursor.execute(query)
        self.db_connection.commit()

    def create_keyword_table(self, category: str, keyword: str):
        """為特定的關鍵字創建資料表 (使用 MySQL 動態 SQL)"""
        # 如果 category 是列表，取第一個元素
        if isinstance(category, list):
            category = category[0]

        table_name = self.get_table_name(keyword)  # 生成資料表名稱
        # 如果 table_name 是列表，取第一個元素
        if isinstance(table_name, list):
            table_name = table_name[0]

        # 切換到指定的 category 資料庫 (這邊直接用 f-string)
        use_db_query = f"USE `{category}`"
        self.db_cursor.execute(use_db_query)
        print(f"已成功切換到資料庫：{category}")

        # 組合動態 SQL 指令，注意這裡直接將 table_name 插入，並用反引號包裹以避免特殊字符問題
        create_table_sql = (
            f"CREATE TABLE `{table_name}` ("
            "id INT AUTO_INCREMENT PRIMARY KEY, "
            "title VARCHAR(255) NOT NULL, "
            "description TEXT, "
            "link VARCHAR(255), "
            "keyword VARCHAR(255) NOT NULL, "
            "likes INT, "
            "views INT, "
            "difficulty FLOAT DEFAULT 5, "
            "recommendation FLOAT DEFAULT 5, "
            "watch INT)"
        )

        # 將動態 SQL 指令存入 MySQL 變數 @sql
        set_sql_query = "SET @sql = %s"
        self.db_cursor.execute(set_sql_query, (create_table_sql,))

        # 使用 PREPARE 語句準備執行 @sql 中的指令
        self.db_cursor.execute("PREPARE stmt FROM @sql")
        # 執行預處理好的語句
        self.db_cursor.execute("EXECUTE stmt")
        # 釋放預處理語句
        self.db_cursor.execute("DEALLOCATE PREPARE stmt")

        self.db_connection.commit()
        print(f"資料表 `{table_name}` 已在資料庫 `{category}` 中建立。")

    def check_keyword_exists(self, category: str, keyword: str) -> bool:
        """檢查資料庫中是否存在指定關鍵字的資料表"""
        table_name = self.get_table_name(keyword)
        # 修正：將 category 轉換為元組
        category_param = (category,) if isinstance(category, str) else category
        query = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s"
        self.db_cursor.execute(
            query,
            (
                category_param[0],
                table_name[0] if isinstance(table_name, list) else table_name,
            ),
        )
        result = self.db_cursor.fetchone()
        return result[0] > 0

    def get_table_name(self, keyword: str) -> str:
        """為關鍵字創建一個唯一的資料表名稱"""
        return keyword.replace(
            " ", "_"
        ).lower()  # 用關鍵字創建資料表名稱，並將空格替換為下劃線

    def insert_keyword_data(self, category: str, keyword: str, video_data: List[Dict]):
        """插入影片資料到指定關鍵字的資料表"""
        # 切換到指定的 category 資料庫 (這邊直接用 f-string)
        use_db_query = f"USE `{category[0]}`"
        self.db_cursor.execute(use_db_query)
        print(f"已成功切換到資料庫：{category}準備創建資料欄")
        table_name = self.get_table_name(keyword)
        query = f"INSERT INTO {table_name} (title, description, link, keyword, likes, views, difficulty, recommendation, watch) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        for data in video_data:
            likes = data.get("likes", 0) or 0
            views = data.get("views", 1) or 1  # 避免 views 為 0，防止除零錯誤
            recommendation = min(10, max(1, (likes / views) * 100))  # 計算推薦值

            values = (
                data.get("title"),
                data.get("description"),
                data.get("id"),
                keyword,
                likes,
                views,
                data.get("difficulty", 5),
                recommendation,  # 新增計算後的推薦值
                data.get("watch", 0),
            )
            self.db_cursor.execute(query, values)
            print(f"已存儲資料：{keyword}")
        self.db_connection.commit()

    def get_keyword_data(self, category: str, keyword: str):
        """從資料表中獲取指定關鍵字的影片資料，並根據推薦度排序"""
        try:
            # 使用參數化查詢，避免SQL注入風險
            self.db_cursor.execute(f"USE `{category}`")
            table_name = self.get_table_name(keyword)

            # 添加ORDER BY子句根據recommendation欄位排序
            query = f"""
            SELECT title, description, link, likes, views, difficulty, recommendation, watch 
            FROM {table_name}
            ORDER BY recommendation DESC 
            """

            # 執行查詢
            self.db_cursor.execute(query)
            results = self.db_cursor.fetchall()

            # 返回排序後的查詢結果的字典列表
            return [
                {
                    "title": result[0],
                    "description": result[1],
                    "link": result[2],
                    "likes": result[3],
                    "views": result[4],
                    "difficulty": result[5],
                    "recommendation": result[6],
                    "watch": result[7],
                }
                for result in results
            ]

        except Exception as e:
            # 捕捉錯誤並顯示錯誤信息
            print(f"An error occurred: {e}")
            return []

