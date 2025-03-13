# EduShield
Use AI to teach, recommend videos, and filter inappropriate information for children

![EduShield_logo_no_bg (1)](https://github.com/user-attachments/assets/49916e4e-8c65-439c-9238-a9ff7e4df45d)

產頻名稱:EduShield ｜ 智能保護及學習資源推薦平台

產品說明:
在這個資訊爆炸且有毒的網路環境裡，孩子們身心靈的安危是全世界所有家長們共同面對的困境，一味地限制他們上網的方式並不能解決問題，因為線上學習以及興趣探索已經是未來的趨勢。
因此EduShield透過AI技術可以過濾不當資訊及影片，提供最符合孩子需求的學習資源，讓他們在一個相對安全的網路環境裡，慢慢學習如何判斷各種資訊。

程式架構:
程式分成兩塊，一塊是program，通過執行member.py，可以在地端開啟網頁，並通過註冊使用者資訊及小孩資訊，會將資料存入mongoDB，同時我們通過line admin的功能可以取得用戶line ID，
並於其他程式對照用戶line ID來確認用戶權限及相關資訊。
程式另一塊是LineAI，我們使用RAG、embedding以及語意分析等技術，讓AI做到知識傳遞、過濾不當資訊及影片、判斷用戶學習程度、精準於YouTube下關鍵字、演算推薦最合適的5支影片...等功能，
這部分需要執行lineDB.py檔案，同時使用ngrok將網址設定到本產品的line官方帳號的webhook上，然後即可於line上使用此產品服務。

其他參考檔案:
1.Demo影片
2.Demo網站(EduShield.zip)
