from openai import OpenAI

from app.config import settings

client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
for m in sorted(client.models.list().data, key=lambda m: m.id):
    print(m.id)
