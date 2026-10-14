import json
import time
from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from app.schemas import CarAttributes, SellerInput
from app.tools import AgentState, run_tool, tool_specs

client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
MAX_STEPS = 10
LOW_CONFIDENCE = 0.7

SYSTEM_PROMPT = """You are ListPilot, an agent that prepares used-car listings for an Indian marketplace.
You receive attributes extracted from the car's photos and the seller's details.

Process:
1. Validate the registration number.
2. Check the odometer reading.
3. Estimate the price band.
4. Call flag_for_inspection for anything suspicious: invalid registration, abnormal mileage,
   pricing failure, or any damage.
5. Write the listing and call submit_listing. If rejected, fix every issue and resubmit.

Rules: describe only what is in the attributes or seller notes. Never invent features.
Do not mention variant or trim (e.g. M135, ZXi, SX) unless the seller notes state it.
Never include the registration number in the listing. Avoid subjective claims like
'excellent condition'. Always disclose damage. Never write prices in the listing text."""


@dataclass
class AgentResult:
    state: AgentState
    trace: list[dict]
    steps: int
    latency_s: float
    input_tokens: int
    output_tokens: int

    @property
    def status(self) -> str:
        if self.state.listing is None:
            return "failed"
        if any(f["severity"] == "high" for f in self.state.flags):
            return "needs_review"
        return "ready_to_publish"


def run_agent(attributes: CarAttributes, seller: SellerInput) -> AgentResult:
    state = AgentState(attributes=attributes, seller=seller)

    # deterministic safety: low-confidence fields are flagged by code, not by the LLM
    for fld, conf in attributes.confidence.model_dump().items():
        if conf < LOW_CONFIDENCE:
            state.flags.append(
                {
                    "reason": f"low confidence on {fld} ({conf:.2f})",
                    "severity": "high",
                    "by": "system",
                }
            )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "photo_attributes": attributes.model_dump(),
                    "seller": seller.model_dump(),
                    "system_flags": state.flags,
                }
            ),
        },
    ]
    trace, in_tok, out_tok, start = [], 0, 0, time.perf_counter()

    for step in range(1, MAX_STEPS + 1):
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tool_specs(),
            tool_choice="auto",
            temperature=0,
        )
        in_tok += resp.usage.prompt_tokens
        out_tok += resp.usage.completion_tokens
        msg = resp.choices[0].message

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content or ""})
            messages.append(
                {
                    "role": "user",
                    "content": "Continue. Finish by calling submit_listing.",
                }
            )
            continue

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments,
                        },
                    }
                    for c in msg.tool_calls
                ],
            }
        )

        for call in msg.tool_calls:
            t0 = time.perf_counter()
            result = run_tool(call.function.name, call.function.arguments, state)
            trace.append(
                {
                    "step": step,
                    "tool": call.function.name,
                    "args": call.function.arguments,
                    "result": result,
                    "ms": round((time.perf_counter() - t0) * 1000),
                }
            )
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )

        if state.listing is not None:
            break

    return AgentResult(state, trace, step, time.perf_counter() - start, in_tok, out_tok)
