import google.generativeai as genai
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiAPI:
    def __init__(self, api_key: str):
        """Gemini APIクライアントの初期化"""
        genai.configure(api_key=api_key)
        
        # 優先順位の高いモデル名から試す
        model_names = [
            'gemini-2.5-pro',
            'models/gemini-2.5-pro',
            'gemini-1.5-pro', 
            'gemini-1.5-flash',
            'gemini-pro',
            'models/gemini-1.5-pro',
            'models/gemini-1.5-flash',
            'models/gemini-pro'
        ]
        
        self.model = None
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Successfully initialized Gemini model: {model_name}")
                break
            except Exception as e:
                logger.debug(f"Failed to initialize model {model_name}: {e}")
                continue
        
        if self.model is None:
            logger.error("Failed to initialize any Gemini model")
            raise Exception("No available Gemini model found")
        
    def rewrite_description(self, title: str, original_description: str, target_length: int = 180) -> Optional[str]:
        """作品紹介文をリライト"""
        try:
            prompt = f"""以下の同人作品の紹介文を、読者の興味を引くように{target_length}字程度で書き直してください。
エロティックな要素は適度に残しつつ、魅力的で読みやすい文章にしてください。

作品名：{title}
元の紹介文：{original_description}

条件：
- {target_length}字程度で簡潔にまとめる
- 作品の魅力が伝わるように書く
- 読者が「続きを読みたい」と思うような文章にする
- 過度に露骨な表現は避ける"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                rewritten_text = response.text.strip()
                logger.info(f"Successfully rewrote description for: {title}")
                return rewritten_text
            else:
                logger.warning(f"Empty response from Gemini API for: {title}")
                return None
                
        except Exception as e:
            logger.error(f"Error rewriting description: {e}")
            return None
    
    def generate_h2_heading(self, pattern: int = 1) -> str:
        """H2見出しを生成（3パターンから選択）"""
        headings = {
            1: "作品の見どころ",
            2: "この作品のおすすめポイント",
            3: "注目すべき魅力"
        }
        
        return headings.get(pattern, headings[1])