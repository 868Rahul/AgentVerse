from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from ai.llm import get_model, settings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END
from ai.guardrails import GUARDRAIL_RULES, trim_history
from ai.tools.oa_tools import get_user_department, get_user_info, list_handbook_sections, search_handbook
from ai.tools.utility_tools import calculator, get_weather
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
)

#  Agent
math_agent = create_react_agent(
    model=model,
    prompt=(
        "You are a math expert. Solve the user's math question step by step and give the final result clearly. "
        "Use the `calculator` tool for every arithmetic step instead of computing in your head."
        + GUARDRAIL_RULES
    ),
    tools=[calculator],
    name="math_agent",
    pre_model_hook=worker_pre_model_hook,
)

# Programming expert agent
code_agent = create_react_agent(
    model=model,
    prompt="You are a programming expert. Solve the user's programming problem with clear explanations and correct, runnable code." + GUARDRAIL_RULES,
    tools=[],
    name="code_agent",
    pre_model_hook=worker_pre_model_hook,
)

# General agent
general_agent = create_react_agent(
    model=model,
    prompt="You are a helpful general assistant. Answer the user's general knowledge questions clearly and concisely." + GUARDRAIL_RULES,
    tools=[],
    name="general_agent",
    pre_model_hook=worker_pre_model_hook,
)

# Weather agent
weather_agent = create_react_agent(
    model=model,
    prompt=(
        "You are a weather assistant. Use the `get_weather` tool for current weather and forecasts of any place "
        "(add the country when a name is ambiguous, e.g. 'Paris, France'). Report temperature in °C, feels-like, humidity, "
        "wind and chance of rain, and say the data is from Open-Meteo. Never invent weather data."
        + GUARDRAIL_RULES
    ),
    tools=[get_weather, calculator],
    name="weather_agent",
    pre_model_hook=worker_pre_model_hook,
)


workers = [hr_agent, weather_agent, general_agent, code_agent, math_agent]

# Create a supervisor
supervisor = create_supervisor(
    agents=workers,
    model=model,
    # full_history full message record, last_message output of the last agent
    output_mode="last_message",
    prompt=(
       """
You are the supervisor of a team of agents:
- hr_agent: company policies and the Employee Handbook (working hours, leave, vacation, benefits, salary, conduct,
  resignation, IT/internet use ...) and questions about employees or departments.
- weather_agent: current weather and forecasts for any city or place.
- math_agent: math, calculations, percentages, algebra, statistics (has an exact calculator).
- code_agent: programming, algorithms, debugging, code.
- general_agent: any other general knowledge question.

Rules:
- Greetings, thanks and "what can you do?" questions: answer yourself, briefly, without delegating. Explain that the team
  can answer company policy / HR questions from the Employee Handbook, look up employees, give weather forecasts,
  calculate and solve math, help with code and answer general questions.
- Otherwise delegate to exactly one agent; anything about the company, work rules or colleagues goes to hr_agent.
- Only one tool can be called at a time; multiple tools cannot be called in parallel.
        """ + GUARDRAIL_RULES
    ),

    add_handoff_back_messages=False,
    parallel_tool_calls=False,
    pre_model_hook=supervisor_pre_model_hook,

)

checkpointer = InMemorySaver()

# By default every worker hands control back to the supervisor, which then spends one more model call
# just to repeat the worker's answer. End the run as soon as a worker has answered instead:
# saves a full LLM round trip per question, and the worker's answer is what the user sees.
for worker in workers:
    supervisor.edges.discard((worker.name, "supervisor"))
    supervisor.add_edge(worker.name, END)

supervisor_agent = supervisor.compile(checkpointer=checkpointer)
