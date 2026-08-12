
"""Swappable LLM backend."""
from app.config import settings


def chat(messages: list[dict], temperature: float = 0.3) -> str:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return _chat_ollama(messages, temperature)
    elif provider == "openai":
        return _chat_openai(messages, temperature)
    elif provider == "anthropic":
        return _chat_anthropic(messages, temperature)
    elif provider == "gemini":
        return _chat_gemini(messages, temperature)
    elif provider == "groq":
        return _chat_groq(messages, temperature)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _chat_ollama(messages, temperature):
    import ollama
    client = ollama.Client(host=settings.OLLAMA_HOST)
    response = client.chat(
        model=settings.OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature},
    )
    return response["message"]["content"]


def _chat_openai(messages, temperature):
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _chat_anthropic(messages, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        system=system or None,
        messages=turns,
        max_tokens=1024,
        temperature=temperature,
    )
    return response.content[0].text


def _chat_gemini(messages, temperature):
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [m for m in messages if m["role"] != "system"]
    model = genai.GenerativeModel(settings.GEMINI_MODEL, system_instruction=system or None)
    if not turns:
        response = model.generate_content(
            "Begin the conversation now, following your instructions.",
            generation_config={"temperature": temperature},
        )
        return response.text
    history = []
    for m in turns[:-1]:
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})
    chat_session = model.start_chat(history=history)
    last_message = turns[-1]["content"]
    response = chat_session.send_message(
        last_message, generation_config={"temperature": temperature}
    )
    return response.text


def _chat_groq(messages, temperature):
    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
