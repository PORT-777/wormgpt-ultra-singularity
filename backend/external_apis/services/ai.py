"""Phase 2 — AI / ML external API specifications.

URLs follow each vendor's public documentation and are declarative only: a
missing key disables the service without affecting the platform. Configure
keys in backend/.env (see .env.example).
"""
from __future__ import annotations

from ..registry import ServiceSpec, registry


def register_ai_services() -> None:
    # 2A — language & NLP
    registry.register(ServiceSpec(
        name="openai", category="nlp", base_url="https://api.openai.com/v1",
        endpoints={"chat": "{base}/chat/completions",
                   "embed": "{base}/embeddings",
                   "vision": "{base}/chat/completions",
                   "function": "{base}/chat/completions"},
        key_env="OPENAI_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="anthropic", category="nlp", base_url="https://api.anthropic.com/v1",
        endpoints={"chat": "{base}/messages"}, key_env="ANTHROPIC_API_KEY",
        auth_style="header", key_param="x-api-key", method="POST"))
    registry.register(ServiceSpec(
        name="cohere", category="nlp", base_url="https://api.cohere.com/v2",
        endpoints={"generate": "{base}/chat", "classify": "{base}/classify",
                   "embed": "{base}/embed", "summarize": "{base}/summarize",
                   "rerank": "{base}/rerank"},
        key_env="COHERE_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="huggingface", category="nlp", base_url="https://api-inference.huggingface.co",
        endpoints={"infer": "{base}/models/{model}"},
        key_env="HUGGINGFACE_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="nlpcloud", category="nlp", base_url="https://api.nlpcloud.io/v1",
        endpoints={"sentiment": "{base}/{model}/sentiment",
                   "ner": "{base}/{model}/entities",
                   "summarize": "{base}/{model}/summarization",
                   "translate": "{base}/{model}/translation",
                   "qa": "{base}/{model}/question-answering"},
        key_env="NLPCLOUD_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="witai", category="nlp", base_url="https://api.wit.ai",
        endpoints={"message": "{base}/message"}, key_env="WITAI_TOKEN",
        auth_style="bearer"))
    registry.register(ServiceSpec(
        name="dialogflow", category="nlp", base_url="https://dialogflow.googleapis.com/v2",
        endpoints={"detect": "{base}/projects/{project}/agent/sessions/{session}:detectIntent"},
        key_env="DIALOGFLOW_PROJECT_ID", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="cloudmersive-nlp", category="nlp", base_url="https://api.cloudmersive.com/nlp-v2",
        endpoints={"language": "{base}/language/detect",
                   "entities": "{base}/entity/recognize",
                   "pos": "{base}/pos/tag"},
        key_env="CLOUDMERSIVE_API_KEY", auth_style="header",
        key_param="Apikey", method="POST"))
    registry.register(ServiceSpec(
        name="perspective", category="moderation",
        base_url="https://commentanalyzer.googleapis.com/v1alpha1",
        endpoints={"toxicity": "{base}/comments:analyze"},
        key_env="PERSPECTIVE_API_KEY", auth_style="query", key_param="key",
        method="POST"))
    registry.register(ServiceSpec(
        name="wolfram", category="compute", base_url="https://api.wolframalpha.com/v2",
        endpoints={"query": "{base}/query"}, key_env="WOLFRAM_APP_ID",
        auth_style="query", key_param="appid"))

    # 2B — vision & image
    registry.register(ServiceSpec(
        name="clarifai", category="vision", base_url="https://api.clarifai.com/v2",
        endpoints={"classify": "{base}/models/general-image-recognition/outputs"},
        key_env="CLARIFAI_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="imagga", category="vision", base_url="https://api.imagga.com/v2",
        endpoints={"tag": "{base}/tags", "color": "{base}/colors"},
        key_env="IMAGGA_API_KEY", auth_style="header", key_param="Authorization"))
    registry.register(ServiceSpec(
        name="skybiometry", category="vision", base_url="https://api.skybiometry.com/fc",
        endpoints={"face": "{base}/faces/detect"}, key_env="SKYBIOMETRY_API_KEY",
        auth_style="query", key_param="api_key"))
    registry.register(ServiceSpec(
        name="roboflow", category="vision", base_url="https://detect.roboflow.com",
        endpoints={"detect": "{base}/{model}/{version}"},
        key_env="ROBOFLOW_API_KEY", auth_style="query", key_param="api_key",
        method="POST"))
    registry.register(ServiceSpec(
        name="irisnet", category="moderation", base_url="https://api.irisnet.de/v1",
        endpoints={"image": "{base}/moderation/image"}, key_env="IRISNET_API_KEY",
        auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="inferdo", category="vision", base_url="https://api.inferdo.com/v1",
        endpoints={"analyze": "{base}/analyze"}, key_env="INFERDO_API_KEY",
        auth_style="bearer", method="POST"))

    # 2C — speech & audio
    registry.register(ServiceSpec(
        name="google-stt", category="audio", base_url="https://speech.googleapis.com/v1",
        endpoints={"transcribe": "{base}/speech:recognize"},
        key_env="GOOGLE_SPEECH_API_KEY", auth_style="query", key_param="key",
        method="POST"))
    registry.register(ServiceSpec(
        name="gladia", category="audio", base_url="https://api.gladia.io/v2",
        endpoints={"transcribe": "{base}/transcription",
                   "gladia": "{base}/transcription"},
        key_env="GLADIA_API_KEY", auth_style="header",
        key_param="x-gladia-key", method="POST"))
    registry.register(ServiceSpec(
        name="assemblyai", category="audio", base_url="https://api.assemblyai.com/v2",
        endpoints={"assembly": "{base}/transcript"},
        key_env="ASSEMBLYAI_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="gandr", category="audio", base_url="https://api.gandr.ai/v1",
        endpoints={"tts": "{base}/tts"}, key_env="GAND_R_API_KEY",
        auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="wavespeed", category="generation", base_url="https://api.wavespeed.ai/api/v3",
        endpoints={"generate": "{base}/{model}"}, key_env="WAVESPEED_API_KEY",
        auth_style="bearer", method="POST"))

    # 2D — routers
    registry.register(ServiceSpec(
        name="openrouter", category="router", base_url="https://openrouter.ai/api/v1",
        endpoints={"route": "{base}/chat/completions"},
        key_env="OPENROUTER_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="aimlapi", category="router", base_url="https://api.aimlapi.com/v1",
        endpoints={"aiml": "{base}/chat/completions"},
        key_env="AIMLAPI_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="xiurouter", category="router", base_url="https://api.xiurouter.com/v1",
        endpoints={"xiu": "{base}/chat/completions"},
        key_env="XIUROUTER_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="unorouter", category="router", base_url="https://api.unorouter.com/v1",
        endpoints={"uno": "{base}/chat/completions"},
        key_env="UNOROUTER_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="edenai", category="router", base_url="https://api.edenai.run/v2",
        endpoints={"eden": "{base}/text/generation"},
        key_env="EDENAI_API_KEY", auth_style="bearer", method="POST"))

    # 2E — specialized / keyless
    registry.register(ServiceSpec(
        name="spamhunter", category="moderation", base_url="https://spamhunter-api.vercel.app",
        endpoints={"spam": "{base}/api/check"}, health_path="{base}/api/health"))
    registry.register(ServiceSpec(
        name="summarize-ai", category="text", base_url="https://api.summarize-ai.com/v1",
        endpoints={"summarize": "{base}/summarize"},
        key_env="SUMMARIZE_AI_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="customgpt", category="rag", base_url="https://api.customgpt.ai/api/v3",
        endpoints={"rag": "{base}/agents/{agent}/chat"},
        key_env="CUSTOMGPT_API_KEY", auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="ai-learning-engine", category="education",
        base_url="https://api.ailearningengine.com/v1",
        endpoints={"grade": "{base}/grade"}, key_env="AILE_API_KEY",
        auth_style="bearer", method="POST"))
    registry.register(ServiceSpec(
        name="limitreset", category="monitoring",
        base_url="https://limitreset.vercel.app",
        endpoints={"limits": "{base}/api/board"}, health_path="{base}/api/board"))
    registry.register(ServiceSpec(
        name="openrouter-models", category="models",
        base_url="https://openrouter.ai/api/v1",
        endpoints={"list": "{base}/models"}, health_path="{base}/models"))
    registry.register(ServiceSpec(
        name="pollinations", category="generation", base_url="https://image.pollinations.ai",
        endpoints={"generate": "{base}/prompt/{prompt}"},
        health_path="{base}/prompt/test"))
