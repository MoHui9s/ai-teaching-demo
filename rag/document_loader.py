"""RAG 系统 —— 文档加载器（预置知识库）"""

import logging
from typing import List, Dict
from pathlib import Path

from rag.embeddings import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger("rag-loader")

# 预置语法知识
GRAMMAR_RULES = [
    {
        "id": "grammar_present_simple",
        "text": "一般现在时 (Simple Present)：主语 + 动词原形/动词+s。I go to school every day. / She goes to school every day. 用于表达习惯、事实、规律性的动作。注意第三人称单数加 -s/-es。",
        "category": "时态",
        "level": "beginner",
    },
    {
        "id": "grammar_past_simple",
        "text": "一般过去时 (Simple Past)：主语 + 动词过去式。I went to school yesterday. 规则动词加 -ed（walked, played），不规则动词需特别记忆（go→went, eat→ate, see→saw）。",
        "category": "时态",
        "level": "beginner",
    },
    {
        "id": "grammar_present_perfect",
        "text": "现在完成时 (Present Perfect)：主语 + have/has + 过去分词。I have visited Beijing. 用于表示过去发生的动作对现在有影响。常见信号词：already, yet, ever, never, since, for。",
        "category": "时态",
        "level": "intermediate",
    },
    {
        "id": "grammar_articles",
        "text": "冠词 (Articles)：a/an（泛指单数可数名词），the（特指）。I saw a dog. The dog was brown. 不可数名词和复数泛指不用冠词：I like music. Dogs are loyal.",
        "category": "语法",
        "level": "beginner",
    },
    {
        "id": "grammar_conditionals",
        "text": "条件句 (Conditionals)：第一条件句 If + 一般现在时, will + 动词原形。If it rains, I will stay home. 用于表达真实可能的情况。第二条件句 If + 过去式, would + 动词原形，用于假设。",
        "category": "语法",
        "level": "intermediate",
    },
    {
        "id": "grammar_relative_clauses",
        "text": "定语从句 (Relative Clauses)：用 who/that（指人）, which/that（指物）, where（指地点）连接。The man who lives next door is a doctor. The book that I read was great.",
        "category": "语法",
        "level": "intermediate",
    },
    {
        "id": "grammar_modal_verbs",
        "text": "情态动词 (Modal Verbs)：can（能力/许可）, must（必须）, should（应该）, may（可能/许可）, might（可能/更不确定）。You should practice English every day. You mustn't give up.",
        "category": "语法",
        "level": "intermediate",
    },
    {
        "id": "grammar_passive_voice",
        "text": "被动语态 (Passive Voice)：be + 过去分词。The letter was written by Tom. 当不知道或不需要强调动作执行者时使用。English is spoken worldwide.",
        "category": "语法",
        "level": "advanced",
    },
]

# 预置发音知识
PRONUNCIATION_TIPS = [
    {
        "id": "pron_th",
        "text": "th 清辅音 /θ/：舌尖放在上下齿之间，气流从缝隙中挤出，声带不振动。如 think, three, thank。常见错误：发成 /s/（sink）或 /f/（fink）。练习技巧：对着镜子看舌尖是否露出。",
        "category": "辅音",
    },
    {
        "id": "pron_r_l",
        "text": "r 和 l 的区别：/r/ 舌尖卷起靠近上颚但不接触，嘴唇微微收圆（right）；/l/ 舌尖抵住上齿龈（light）。练习：反复读 'red lorry yellow lorry'。词尾 dark l（well, call）舌尖必须抬起触及上齿龈。",
        "category": "辅音",
    },
    {
        "id": "pron_v_w",
        "text": "v 和 w 的区别：/v/ 上齿轻咬下唇，声带振动（very）；/w/ 双唇收圆后迅速张开，不咬唇（wet）。常见错误：very 发成 wery。练习：very well → 注意 v 咬唇、w 收圆嘴。",
        "category": "辅音",
    },
    {
        "id": "pron_long_short_vowels",
        "text": "长短元音区别：/iː/ 长元音，嘴角拉开（sheep, eat）；/ɪ/ 短元音，嘴巴放松（ship, it）。/uː/ 长（food, too）；/ʊ/ 短（foot, book）。练习最小对立对：sheep-ship, feet-fit, pool-pull。",
        "category": "元音",
    },
    {
        "id": "pron_linking",
        "text": "连读 (Linking)：前词以辅音结尾 + 后词以元音开头，连在一起读。如 'turn‿off', 'get‿up', 'an‿apple'。练习：'Pick it up' → 'Pi-ki-tup'。这让英语听起来更流畅自然。",
        "category": "连读",
    },
    {
        "id": "pron_stress",
        "text": "单词重音 (Word Stress)：多音节词中一个音节重读，音更高更长更响亮。如 phoTOgraphy（重音在第二音节），PHOtograph（重音在第一音节）。错误的重音会导致难以理解。",
        "category": "重音",
    },
    {
        "id": "pron_schwa",
        "text": "弱读音 /ə/ (Schwa)：英语中最常见的元音，出现在非重读音节。如 banana → /bəˈnænə/, about → /əˈbaʊt/。掌握弱读是提高发音自然度的关键。",
        "category": "元音",
    },
]


class DocumentLoader:
    """知识库文档加载器"""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()

    def load_all(self):
        """加载所有知识库到向量存储"""
        logger.info("开始加载知识库...")

        self._load_grammar()
        self._load_pronunciation()

        logger.info("知识库加载完成")

    def _load_grammar(self):
        """加载语法规则"""
        texts = [r["text"] for r in GRAMMAR_RULES]
        metadatas = [
            {"source": r["id"], "category": r["category"], "level": r["level"]}
            for r in GRAMMAR_RULES
        ]
        ids = [r["id"] for r in GRAMMAR_RULES]

        embeddings = self.embedding_service.embed(texts)
        self.vector_store.add_documents(
            collection_name="grammar",
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"已加载 {len(GRAMMAR_RULES)} 条语法规则")

    def _load_pronunciation(self):
        """加载发音知识"""
        texts = [r["text"] for r in PRONUNCIATION_TIPS]
        metadatas = [
            {"source": r["id"], "category": r["category"]}
            for r in PRONUNCIATION_TIPS
        ]
        ids = [r["id"] for r in PRONUNCIATION_TIPS]

        embeddings = self.embedding_service.embed(texts)
        self.vector_store.add_documents(
            collection_name="pronunciation",
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"已加载 {len(PRONUNCIATION_TIPS)} 条发音技巧")

    @staticmethod
    def get_grammar_rules() -> List[Dict]:
        """获取语法规则列表（非向量）"""
        return GRAMMAR_RULES

    @staticmethod
    def get_pronunciation_tips() -> List[Dict]:
        """获取发音技巧列表（非向量）"""
        return PRONUNCIATION_TIPS


# 全局实例
_document_loader: DocumentLoader = None


def get_document_loader() -> DocumentLoader:
    """获取文档加载器单例"""
    global _document_loader
    if _document_loader is None:
        _document_loader = DocumentLoader()
    return _document_loader
