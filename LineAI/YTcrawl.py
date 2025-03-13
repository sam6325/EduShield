import yt_dlp
import json


def youtube_search(query, max_results=1):
    """使用 yt_dlp 進行 YouTube 搜尋，回傳字典格式"""
    ydl_opts = {
        "quiet": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

        if not result.get("entries"):
            print("沒有找到相關的影片。")
            return {"videos": []}

        videos = []

        for video in result["entries"]:
            video_title = video.get("title", "無標題")
            video_id = video.get("id", "")
            video_url = (
                f"https://www.youtube.com/watch?v={video_id}" if video_id else "無網址"
            )
            video_views = video.get("view_count", 0)
            video_likes = video.get("like_count", 0)
            video_description = video.get("description", "無描述")

            print(f"✅ 影片標題: {video_title}")
            print(f"🔗 影片ID: {video_id}")
            print(f"🔗 影片連結: {video_url}")
            print(f"👁️ 觀看次數: {video_views}")
            print(f"👍 讚數: {video_likes}")
            print(f"📝 描述: {video_description}")
            print("=" * 50)

            videos.append(
                {
                    "title": video_title,
                    "id": video_id,
                    "link": video_url,
                    "description": video_description,
                    "likes": video_likes,
                    "views": video_views,
                }
            )

        return {"videos": videos}  # **回傳字典格式**
