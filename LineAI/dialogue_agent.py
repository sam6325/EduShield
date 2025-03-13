from openai import OpenAI
from openai import APIConnectionError, APIError
from pydantic import BaseModel, Field, PrivateAttr
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from typing import List, Dict
import numpy as np
import re
from YTcrawl import youtube_search
from datetime import datetime
import json
from database_manager import DatabaseManager
from typing import List
from typing import ClassVar


class DialogueAgent(BaseModel):
    """對話代理類，負責處理持續對話邏輯"""

    _openai_client: OpenAI = PrivateAttr()
    _history_file: str = PrivateAttr("dialogue_history.json")
    _system_prompt: str = PrivateAttr(
        """
    你是個嚴謹的知識分析助手，需要：
    1. 盡量多進行幾輪對話來確認清楚用戶的需求
    2. 根據用戶問題判斷知識領域（科學/歷史/藝術）
    3. 根據用戶前面幾句的提問內容自動判斷學習程度（不懂、入門、中等、進階）
    4. 根據學習程度和前面幾輪的對話生成適合的 YouTube 搜尋關鍵字
    5. 禁止提供及查詢有關人類性行為方面的內容
    6. 如果用戶明確要求影片，優先推薦影片
    對話過程要自然流暢，用中文繁體回應。
    """
    )
    conversation_history: list = Field(
        default_factory=list
    )  # 使用 Pydantic default_factory 初始化
    video_data: list = Field(default_factory=list)  # 影片資料
    db_manager: ClassVar[DatabaseManager] = (
        DatabaseManager()
    )  # 使用 ClassVar 進行類型註解

    def __init__(self, api_key: str):
        super().__init__()
        self.conversation_history = []
        if not api_key.startswith("sk-"):
            raise ValueError("無效的 OpenAI API 密鑰！請確保密鑰以 'sk-' 開頭。")
        self._openai_client = OpenAI(api_key=api_key)
        self._load_video_data()  # 初始化時載入影片資料

    def _load_video_data(self, keywords: list = None, category: str = None):
        """載入影片資料，但不進行資料庫操作"""
        if not keywords or not category:
            print("⚠️ 未提供完整參數，跳過資料載入。")
            return

        # 簡化為只檢查資料庫中是否有資料
        category_name = category[0] if isinstance(category, list) else category

        # 從資料庫中讀取已存在的資料
        for keyword in keywords:
            keyword_str = keyword[0] if isinstance(keyword, list) else keyword
            if self.db_manager.check_category_exists(
                category_name
            ) and self.db_manager.check_keyword_exists(category_name, keyword_str):
                print(f"✅ 資料庫中已存在 {category_name}/{keyword_str} 的資料。")
                existing_data = self.db_manager.get_keyword_data(
                    category_name, keyword_str
                )
                if existing_data:
                    self.video_data = existing_data
                    return self.video_data

        # 若資料庫中沒有數據，則返回空列表
        print(f"⚠️ 資料庫中不存在相關資料，需要進行搜尋...")
        self.video_data = []

    def _get_embedding(self, text: str) -> List[float]:
        """使用 OpenAI 獲取文本嵌入向量"""
        try:
            response = self._openai_client.embeddings.create(
                input=text, model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ 獲取嵌入向量失敗: {e}")
            return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _find_best_video_match(self, query: str) -> List[dict]:
        """
        根據歷史對話尋找最匹配的影片，返回前 5 支影片（符合相似度要求）
        遍歷 self.video_data 中的每個 item，再遍歷其中的影片列表。
        """
        if not self.video_data:
            return []

        # 合併最後 3 輪對話作為查詢文本
        recent_history = " ".join(
            [
                msg["content"]
                for msg in self.conversation_history[-3:]
                if msg["role"] in ["user", "assistant"]
            ]
        )

        history_embedding = self._get_embedding(recent_history + " " + query)
        if not history_embedding:
            return []

        candidates = []
        for item in self.video_data:
            videos = item.get("results", {}).get("videos", [])
            for video in videos:
                title = video.get("title", "")
                if not title:
                    continue
                title_embedding = self._get_embedding(title)
                similarity = self._cosine_similarity(history_embedding, title_embedding)
                candidates.append((video, similarity))

        # 按相似度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        # 選出相似度超過閾值（例如 0.7）的前 5 支影片
        top_videos = [video for video, sim in candidates if sim > 0.7][:5]
        print(f"\n🎬 找到 {len(top_videos)} 支相關影片：")
        return top_videos

    def _save_conversation(self):
        """保存對話紀錄到 JSON 文件"""
        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"\n⚠️ 保存對話紀錄失敗: {e}")

    def _generate_response(self, messages: list) -> str:
        """調用 OpenAI API 生成回應"""
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4", messages=messages, temperature=0.7, max_tokens=256
            )
            return response.choices[0].message.content.strip()
        except (APIConnectionError, APIError) as e:
            return f"API錯誤：{str(e)}"

    def _determine_learning_level(self, user_id: str, messages: list) -> str:
        """根據對話內容判斷學習程度，並存入 MySQL"""
        prompt = (
            "根據以下對話內容，判斷用戶的學習程度（不懂、入門、中等、進階）。\n"
            "請直接給出結果，不要解釋。\n"
            f"對話內容：{messages[-1]['content']}"
        )
        response = self._generate_response(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": messages[-1]["content"]},
            ]
        )
        learning_level = response.strip()

        # 存入 MySQL
        try:
            query = (
                "INSERT INTO learning_levels (user_id, learning_level) VALUES (%s, %s)"
            )
            values = (user_id, learning_level)
            self.db_cursor.execute(query, values)
            self.db_connection.commit()
            print(f"✅ 學習程度存入資料庫: {user_id} - {learning_level}")
        except Exception as e:
            print(f"⚠️ 存入學習程度失敗: {e}")

        return learning_level

    def _generate_keywords_with_langchain(self, messages: list) -> str:
        """使用 LangChain 生成推薦關鍵字"""
        examples = [
            {
                "question": "請根據歷史對話內容判斷，什麼樣的關鍵字最適合在 YouTube 上搜尋影片？並判斷此內容屬於哪個知識領域",
                "answer": "關鍵字: 畫畫入門|類別: 藝術",
            },
            {
                "question": "請根據歷史對話內容判斷，什麼樣的關鍵字最適合在 YouTube 上搜尋影片？並判斷此內容屬於哪個知識領域",
                "answer": "關鍵字: 地震類型介紹|類別: 地理",
            },
            {
                "question": "請根據歷史對話內容判斷，什麼樣的關鍵字最適合在 YouTube 上搜尋影片？並判斷此內容屬於哪個知識領域",
                "answer": "關鍵字: 蝴蝶的一生|類別: 生物",
            },
        ]

        example_prompt = PromptTemplate.from_template(
            template="Question: {question}\n{answer}",
        )

        prompt = FewShotPromptTemplate(
            examples=examples,
            example_prompt=example_prompt,
            suffix="Question: {input}",
            input_variables=["input"],
        )

        final_prompt = prompt.format(
            input=f"請根據{self.conversation_history}的內容判斷，哪個關鍵字最適合在 YouTube 上搜尋影片並推薦給用戶？格式必須為「關鍵字: xxx|類別: yyy」"
        )
        response = self._generate_response(
            [
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": messages[-1]["content"]},
            ]
        )
        return response.strip()

    def _extract_keywords_and_category(self, response: str) -> dict:
        """從回應中提取關鍵字和類別"""
        keyword_match = re.search(r"關鍵字\s*[:：]\s*([^|類別]+)", response)
        category_match = re.search(r"類別\s*[:：]\s*([^|]+)", response)
        keywords = keyword_match.group(1).strip() if keyword_match else ""
        category = category_match.group(1).strip() if category_match else ""
        return {"keywords": keywords, "category": category}

    def _perform_youtube_search(self, keywords: List[str], category: str = None):
        """
        使用 Selenium 進行 YouTube 搜尋，並處理資料庫存取
        整合了原本 _load_video_data 中的資料判斷與存取功能
        """
        print("\n🔍 正在使用以下關鍵字進行 YouTube 搜尋：")

        if not category:
            print("⚠️ 未提供類別，無法進行資料庫操作。")
            return self._perform_raw_search(keywords)

        # 修正：確保 category 是字串類型
        category_name = category[0] if isinstance(category, list) else category

        # 檢查並創建資料庫
        if not self.db_manager.check_category_exists(category_name):
            print(f"⚠️ 資料庫 {category_name} 不存在，創建資料庫...")
            self.db_manager.create_category_database(category_name)

        all_results = []  # 存儲所有關鍵字的搜尋結果

        for keyword in keywords:
            keyword_str = keyword if isinstance(keyword, str) else keyword[0]
            print(f"- {keyword_str}")

            # 檢查資料表是否存在 - 修正：將 category_name 放入元組中
            if self.db_manager.check_keyword_exists((category_name,), keyword_str):
                print(f"✅ 資料庫中已存在關鍵字 {keyword_str} 的資料表。")
                # 從資料庫中讀取已存在的資料
                existing_data = self.db_manager.get_keyword_data(
                    category_name, keyword_str
                )
                all_results.append(
                    {"keyword": keyword_str, "results": {"videos": existing_data}}
                )
            else:
                print(
                    f"⚠️ 資料庫中不存在關鍵字 {keyword_str} 的資料表，開始創建資料表並爬蟲..."
                )

                # 創建資料表 - 修正：將 category_name 放入列表中
                self.db_manager.create_keyword_table([category_name], keyword_str)

                try:
                    # 執行 YouTube 搜尋並獲取影片資料
                    search_results = self._perform_raw_search([keyword_str])

                    if search_results and search_results[0].get("results", {}).get(
                        "videos", []
                    ):
                        # 將搜尋結果加入 all_results
                        all_results.extend(search_results)

                        # 準備插入資料庫的資料
                        videos_to_insert = (
                            search_results[0].get("results", {}).get("videos", [])
                        )

                        # 插入資料庫 - 修正：將 category_name 放入列表中
                        self.db_manager.insert_keyword_data(
                            [category_name], keyword_str, videos_to_insert
                        )
                        print(f"✅ 關鍵字 {keyword_str} 的資料已成功插入資料庫。")
                    else:
                        print(f"❌ 沒有獲取到有效的搜尋結果，無法插入資料庫。")
                except Exception as e:
                    print(f"❌ 搜尋 {keyword_str} 時發生錯誤: {e}")

        # 更新本地影片資料
        self.video_data = all_results
        return all_results

    def _perform_raw_search(self, keywords: List[str]):
        """執行原始的 YouTube 搜尋，不涉及資料庫操作"""
        all_results = []

        for keyword in keywords:
            keyword_str = keyword if isinstance(keyword, str) else keyword[0]
            print(f"- 執行原始搜尋: {keyword_str}")
            try:
                # 假設 youtube_search 函數會返回一個影片列表
                search_results = youtube_search(
                    keyword_str, max_results=10
                )  # 限制搜尋結果數量
                all_results.append({"keyword": keyword_str, "results": search_results})
            except Exception as e:
                print(f"❌ 搜尋 {keyword_str} 時發生錯誤: {e}")

        return all_results

    def _should_recommend_video(self, messages: list, assistant_response: str) -> bool:
        """
        判斷是否需要推薦影片：
          1. 如果助手生成的回應中包含 "YouTube" 或 "搜尋" 等關鍵詞，則返回 True。
          2. 如果用戶的最新輸入中包含明確要求推薦影片的詞彙（例如 "請推薦"、"推薦影片"、"影片"、"視頻"、"教學"），則返回 True。
        """
        # 判斷助手回應中是否有推薦相關關鍵詞
        if any(keyword in assistant_response for keyword in ["YouTube", "搜尋"]):
            return True

        # 判斷用戶最新輸入中是否包含明確的推薦要求
        last_user_input = messages[-1]["content"]
        explicit_keywords = ["請推薦", "推薦影片", "影片", "視頻", "教學"]
        if any(keyword in last_user_input for keyword in explicit_keywords):
            return True

        return False

    def _generate_and_show_keywords(self) -> dict:
        """
        動態生成並顯示推薦資訊：
        - 從對話中生成推薦關鍵字和知識領域，
        - 根據關鍵字查找最匹配影片（返回前 5 支影片），
        - 並進行 YouTube 搜尋（模擬）。
        推薦完影片後清空對話歷史以避免干擾後續對話。
        """
        response = self._generate_keywords_with_langchain(self.conversation_history)
        extracted_data = self._extract_keywords_and_category(response)

        print(f"\n✨ 推薦搜尋關鍵字：{extracted_data['keywords']}")
        print(f"📚 知識領域：{extracted_data['category']}")

        # 根據推薦關鍵字更新影片資料
        self._load_video_data([extracted_data["keywords"]], extracted_data["category"])
        best_videos = self._find_best_video_match(extracted_data["keywords"])
        # 如果找不到符合條件的影片，就直接使用 self.video_data 作為推薦來源
        if not best_videos:
            best_videos = self.video_data

        if best_videos:
            for idx, video in enumerate(best_videos, start=1):
                print(f"\n🎬 推薦影片 {idx}：{video.get('title', '未知標題')}")
                print(f"🔗 影片連結：{video.get('link', '無連結')}")
                print(best_videos)
        else:
            print("\n⚠️ 沒有找到任何影片，將進行一般搜尋...")
            # 執行一般搜尋，更新資料庫
            self._perform_youtube_search(
                [extracted_data["keywords"]], extracted_data["category"]
            )
            # 重新從資料庫載入影片資料
            self._load_video_data(
                [extracted_data["keywords"]], extracted_data["category"]
            )
            best_videos = self._find_best_video_match(extracted_data["keywords"])
            if not best_videos:
                best_videos = self.video_data
            if best_videos:
                for idx, video in enumerate(best_videos, start=1):
                    print(f"\n🎬 推薦影片 {idx}：{video.get('title', '未知標題')}")
                    print(f"\n🎬 推薦影片 {idx}：{video.get('title', '未知標題')}")
            else:
                print("⚠️ 仍然沒有找到相關影片。")

        # 清空對話歷史
        self.conversation_history = []

        return {
            "keywords": extracted_data["keywords"],
            "recommended_video": (
                [
                    f"🔗 影片連結：http://127.0.0.1:3000/video/{video.get('link', '無連結')}/{extracted_data['keywords']}/{extracted_data['category']}"
                    for video in best_videos[:5]
                ]
                if best_videos
                else None
            ),
        }

    def process_message(self, user_input: str) -> str:
        # 記錄用戶輸入
        self.conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": user_input,
            }
        )

        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self.conversation_history[-4:])  # 保留最近 3 輪對話

        # 生成基本回覆
        basic_response = self._generate_response(messages)
        final_response = basic_response

        # 判斷是否需要推薦影片，並生成推薦資訊
        if self._should_recommend_video(messages, basic_response):
            result = self._generate_and_show_keywords()
            if result["keywords"]:
                final_response += f"\n\n推薦關鍵字：{result['keywords']}"
            if result["recommended_video"]:
                video_links = "\n".join(result["recommended_video"])
                final_response += f"\n推薦影片：\n{video_links}"
            # 推薦完影片後，對話歷史已在 _generate_and_show_keywords 中清空

        else:
            final_response = basic_response
            self.conversation_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "role": "assistant",
                    "content": final_response,
                }
            )

        self._save_conversation()
        return final_response
