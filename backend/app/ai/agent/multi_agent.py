from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from ai.llm import get_model, settings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_supervisor.handoff import create_forward_message_tool
from ai.guardrails import GUARDRAIL_RULES, trim_history
from ai.tools.oa_tools import get_user_department, get_user_info, list_handbook_sections, search_handbook
from langchain_core.messages import AIMessage, HumanMessage


from dotenv import load_dotenv
load_dotenv()

from langchain_core.globals import set_debug
from langchain_core.globals import set_verbose

set_debug(settings.LANGCHAIN_DEBUG)
set_verbose(False)

model = get_model(settings.DEFAULT_MODEL)


def worker_pre_model_hook(state):
    """Send only the recent history to the model, the full history stays in the checkpointer."""
    return {"llm_input_messages": trim_history(state["messages"])}


def supervisor_pre_model_hook(state):
    """
    When a worker hands its answer back, the conversation ends with an AI message.
    Newer Gemini models reject that ("does not support model prefilling"),
    so a short user turn is added for the supervisor's model call only.
    """
    messages = trim_history(state["messages"])
    if messages and isinstance(messages[-1], AIMessage) and not messages[-1].tool_calls:
        messages = messages + [HumanMessage(
            content="If the agent's answer above fully answers my question, reply with exactly that answer. "
                    "Otherwise delegate to the right agent."
        )]
    return {"llm_input_messages": messages}

# HR / company policy agent, same tools as the OA assistant
hr_agent = create_react_agent(
    model=model,
    prompt=(
        "You are the company's HR assistant. Answer questions about company policies using the Employee Handbook "
        "and questions about employees using the employee database. "
        "For any policy question call `search_handbook` first, answer only from the retrieved text, quote numbers exactly "
        "and cite the page, e.g. (Handbook, p. 15). If the handbook does not cover it, say so. "
        "The handbook writes {ORGANIZATION NAME} where the company name would be, just say 'the company'."
        + GUARDRAIL_RULES
    ),
    tools=[search_handbook, list_handbook_sections, get_user_info, get_user_department],
    name="hr_agent",
    pre_model_hook=worker_pre_model_hook,
).with_config(tags=["skip_stream"])

#  Agent
math_agent = create_react_agent(
    model=model,
    prompt="You are a math expert. Solve the user's math question step by step and give the final result clearly." + GUARDRAIL_RULES,
    tools=[],
    name="math_agent",
    pre_model_hook=worker_pre_model_hook,
).with_config(tags=["skip_stream"])

# Programming expert agent
code_agent = create_react_agent(
    model=model,
    prompt="You are a programming expert. Solve the user's programming problem with clear explanations and correct, runnable code." + GUARDRAIL_RULES,
    tools=[],
    name="code_agent",
    pre_model_hook=worker_pre_model_hook,
).with_config(tags=["skip_stream"])

# General agent
general_agent = create_react_agent(
    model=model,
    prompt="You are a helpful general assistant. Answer the user's general knowledge questions clearly and concisely." + GUARDRAIL_RULES,
    tools=[],
    name="general_agent",
    pre_model_hook=worker_pre_model_hook,
).with_config(tags=["skip_stream"])

forwarding_tool = create_forward_message_tool("supervisor") # The argument is the name to assign to the resulting forwarded message

# Create a supervisor
supervisor = create_supervisor(
    agents=[hr_agent, general_agent, code_agent, math_agent],
    model=model,
    # full_history full message record, last_message output of the last agent
    output_mode="last_message",
    prompt=(
       """
You are the supervisor of a team of agents:
- hr_agent: company policies and the Employee Handbook (working hours, leave, vacation, benefits, salary, conduct,
  resignation, IT/internet use ...) and questions about employees or departments.
- math_agent: math, calculations, algebra, statistics.
- code_agent: programming, algorithms, debugging, code.
- general_agent: any other general knowledge question.

Rules:
- Greetings, thanks and "what can you do?" questions: answer yourself, briefly, without delegating. Explain that the team
  can answer company policy / HR questions from the Employee Handbook, look up employees, solve math, help with code and
  answer general questions.
- Otherwise delegate to exactly one agent; anything about the company, work rules or colleagues goes to hr_agent.
- When the agent has answered, return its answer as it is without adding anything.
- Only one tool can be called at a time; multiple tools cannot be called in parallel.
        """ + GUARDRAIL_RULES
    ),

    add_handoff_back_messages=False,
    parallel_tool_calls=False,
    tools=[forwarding_tool],
    pre_model_hook=supervisor_pre_model_hook,

)

checkpointer = InMemorySaver()

supervisor_agent = supervisor.compile(checkpointer=checkpointer)
