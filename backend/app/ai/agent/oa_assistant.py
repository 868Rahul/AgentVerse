from datetime import datetime
from typing import cast, Literal

from langchain_core.prompts import SystemMessagePromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda, RunnableSerializable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from ai.llm import get_model, settings
from ai.tools.oa_tools import get_user_department, get_user_info, list_handbook_sections, search_handbook
from ai.guardrails import GUARDRAIL_RULES, trim_history
from ai.resilience import EMPTY_RESPONSE_MESSAGE, is_empty_ai_message


from langchain_core.globals import set_debug
from langchain_core.globals import set_verbose
set_debug(settings.LANGCHAIN_DEBUG)
set_verbose(False)

import logging
logging.basicConfig(level=logging.DEBUG if settings.LANGCHAIN_DEBUG else logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s[line:%(lineno)d] - %(funcName)s() - %(message)s')
logger = logging.getLogger(__name__)


class AgentState(MessagesState):
    """State of the agent."""

tools = [get_user_info, get_user_department, search_handbook, list_handbook_sections]

def wrap_model(model: BaseChatModel) -> RunnableSerializable[AgentState, AIMessage]:
    model = model.bind_tools(tools)
    preprocessor = RunnableLambda(
        lambda state: [SystemMessage(content=build_instructions())] + trim_history(state["messages"]),
        name="StateModifier",
    )
    return preprocessor | model

instructions = """
You are the OA (office administration) assistant of the company. You help employees with HR and company information.

What you can do (tell the user this when they greet you or ask what you can do):
1. Answer questions about company policies from the official Employee Handbook: working hours, attendance, overtime,
   holidays, vacation, sick/personal/parental/bereavement leave, benefits and insurance, retirement plan, salary and
   performance review, expense reimbursement, resignation and termination, harassment, confidentiality,
   computer, e-mail and internet use.
2. Look up an employee's details (position, department, contact, status, entry date) by name.
3. Find which department an employee belongs to.

How to answer:
- For ANY policy or rules question, call `search_handbook` first with a short specific query, even if you think you know
  the answer. If the first search does not answer the question, try once more with different words.
- Base policy answers only on the handbook text you retrieved. Quote the important numbers and conditions exactly
  and cite the page, e.g. "(Handbook, p. 15)".
- If the handbook does not cover the topic, say so clearly instead of guessing.
- The handbook is a template: it writes "{{ORGANIZATION NAME}}" where the company name would be. Just say "the company".
- Use `list_handbook_sections` when the user asks what topics the handbook covers.
- Use `get_user_info` / `get_user_department` for questions about a specific person.
- Format answers in short Markdown: a direct answer first, then bullet points for details.

The current time is: {current_time}
""" + GUARDRAIL_RULES


def build_instructions() -> str:
    return instructions.format(current_time=datetime.now().strftime("%Y-%m-%d %H:%M"))


async def call_model(state: AgentState, config: RunnableConfig) -> AgentState:
    """This node is to call llm model"""

    m = get_model(config["configurable"].get("model", settings.DEFAULT_MODEL))
    model_runnable = wrap_model(m)
    response = await model_runnable.ainvoke(state, config)

    # Gemini sometimes finishes with neither text nor a tool call, ask once more before giving up
    if is_empty_ai_message(response):
        logger.warning("Model returned an empty response, retrying once")
        response = await model_runnable.ainvoke(state, config)
        if is_empty_ai_message(response):
            response = AIMessage(content=EMPTY_RESPONSE_MESSAGE)

    return {"messages": [response]}



# After "model", if there are tool calls, run "tools". Otherwise END.
def pending_tool_calls(state: AgentState) -> Literal["tools", "done"]:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise TypeError(f"Expected AIMessage, got {type(last_message)}")
    if last_message.tool_calls:
        return "tools"
    return "done"


# Define the graph
agent = StateGraph(AgentState)
agent.add_node("model", call_model)
agent.add_node("tools", ToolNode(tools = tools))

agent.set_entry_point("model")
agent.add_edge("tools", "model")

agent.add_conditional_edges("model", pending_tool_calls, {"tools": "tools", "done": END})


oa_assistant = agent.compile(
    checkpointer=MemorySaver(),
)
oa_assistant.name = "oa_assistant"

# Save the graph as a PNG
# graph_png = oa_assistant.get_graph().draw_mermaid_png()

# with open("graph.png", "wb") as f:
#     f.write(graph_png)
