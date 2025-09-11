import os

from litellm import completion


def litellm_wrapper(messages: list[dict[str, str]]) -> str:
    model = os.environ.get("MODEL_NAME")
    match model:
        case "openai/gpt-4o":
            return gpt4o_completion(messages)
        case "gemini/gemini-2.5-flash":
            return gemini25flash_completion(messages)
    return gemini25flash_completion(messages)


def gpt4o_completion(messages: list[dict[str, str]]) -> str:
    result = completion(
        model="openai/gpt-4o",
        messages=messages,
    )

    return result['choices'][0]['message']['content']

def gemini25flash_completion(messages: list[dict[str, str]]) -> str:
    result = completion(
        model="gemini/gemini-2.5-flash",
        messages=messages
    )

    return result['choices'][0]['message']['content']