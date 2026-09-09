from functools import cache
from typing import TypeAlias


from chromadb.auth import T
from langchain_community.chat_models import FakeListChatModel, tongyi
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_community.chat_models import ChatTongyi
from langchain_google_genai import ChatGoogleGenerativeAI




from core.config import settings
from ai.models import (
    AllModelEnum,
    DeepseekModelName,
    FakeModelName,
    GeminiModelName,
    OllamaModelName,
    OpenAIModelName,
    TongYiModelName,

)

_MODEL_TABLE = {
    OpenAIModelName.GPT_4O_MINI: "gpt-4o-mini",
    OpenAIModelName.GPT_4O: "gpt-4o",
    DeepseekModelName.DEEPSEEK_CHAT: "deepseek-chat",
    OllamaModelName.OLLAMA_GENERIC: "ollama",
    FakeModelName.FAKE: "fake",
    TongYiModelName.QWEN_PLUS: "qwen-plus",
    GeminiModelName.GEMINI_3_6_FLASH: "gemini-3.6-flash",
    GeminiModelName.GEMINI_2_5_FLASH: "gemini-2.5-flash",

}


class FakeToolModel(FakeListChatModel):
    def __init__(self, responses: list[str]):
        super().__init__(responses=responses)

    def bind_tools(self, tools):
        return self

ModelT: TypeAlias = (
    ChatOpenAI | ChatOllama | ChatDeepSeek | FakeToolModel | ChatTongyi | ChatGoogleGenerativeAI
)



@cache
def get_model(model_name: AllModelEnum, /) -> ModelT:
    """
    Get model by model name.
    Args:
        model_name: Model name.
    Returns:
        Model instance.
    """

    
    api_model_name = _MODEL_TABLE.get(model_name)
    if not api_model_name:
        raise ValueError(f"Unsupported model: {model_name}")

    if model_name in OpenAIModelName:
        return ChatOpenAI(model=api_model_name, temperature=0.5, streaming=True)

   
    if model_name in DeepseekModelName:

        return ChatDeepSeek(
            model=api_model_name,
            temperature=0.5,
            streaming=True,
            api_key=settings.DEEPSEEK_API_KEY,
        )
    
    if model_name in OllamaModelName:
        if settings.OLLAMA_BASE_URL:
            chat_ollama = ChatOllama(
                model=settings.OLLAMA_MODEL, temperature=0.5, base_url=settings.OLLAMA_BASE_URL
            )
        else:
            chat_ollama = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0.5)
        return chat_ollama
    if model_name in FakeModelName:
        return FakeToolModel(responses=["This is a test response from the fake model."])
    
    if model_name in TongYiModelName:
        return ChatTongyi(model=api_model_name, temperature=0.5, streaming=True)

    if model_name in GeminiModelName:
        return ChatGoogleGenerativeAI(
            model=api_model_name,
            temperature=0.5,
            google_api_key=settings.GOOGLE_API_KEY,
        )
