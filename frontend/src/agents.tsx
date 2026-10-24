import React from "react";
import { ApartmentOutlined, CloudOutlined, SolutionOutlined } from "@ant-design/icons";

export interface AgentMeta {
  id: string;
  name: string;
  shortName: string;
  tagline: string;
  description: string;
  icon: React.ReactNode;
  suggestions: string[];
}

// ids must match the backend agent registry (backend/app/ai/agent/agents.py)
export const AGENTS: AgentMeta[] = [
  {
    id: "oa-assistant",
    name: "OA Assistant",
    shortName: "HR",
    tagline: "HR policies & employee lookup",
    description:
      "Answers company policy questions from the Employee Handbook with page references, and looks up employees and departments.",
    icon: <SolutionOutlined />,
    suggestions: [
      "How many vacation days do I get?",
      "What are the normal working hours?",
      "What is the sick leave policy?",
      "Which department is Alice in?",
    ],
  },
  {
    id: "weather-calculator",
    name: "Weather & Calculator",
    shortName: "Weather",
    tagline: "Forecasts anywhere · exact math",
    description:
      "Live weather and up to 7-day forecasts for any city (Open-Meteo), plus an exact calculator for percentages, powers, roots and more.",
    icon: <CloudOutlined />,
    suggestions: [
      "What's the weather in Mumbai right now?",
      "Will it rain in London in the next 3 days?",
      "What is 18% GST on 12,499?",
      "Convert 98.6 °F to Celsius",
    ],
  },
  {
    id: "multi-agent-supervisor",
    name: "Multi-Agent Team",
    shortName: "Team",
    tagline: "HR · Weather · Math · Code · General",
    description:
      "A supervisor routes each question to the right specialist: HR (Employee Handbook), weather, math, programming or general knowledge.",
    icon: <ApartmentOutlined />,
    suggestions: [
      "What does the handbook say about overtime?",
      "How hot is it in Delhi today?",
      "Write a Python function that reverses a string",
      "What is the compound interest on 50,000 at 7% for 5 years?",
    ],
  },
];

export const getAgent = (id: string | null | undefined): AgentMeta =>
  AGENTS.find((agent) => agent.id === id) ?? AGENTS[0];

// Supervisor hand-off tools are shown as a "Routed to" tag instead of a tool call
const WORKER_NAMES: Record<string, string> = {
  hr_agent: "HR agent",
  weather_agent: "Weather agent",
  math_agent: "Math agent",
  code_agent: "Code agent",
  general_agent: "General agent",
};

export const isHandoffTool = (name: string) => name.startsWith("transfer_to_") || name.startsWith("transfer_back_to_");

export const handoffTarget = (name: string) => {
  const worker = name.replace("transfer_to_", "");
  return WORKER_NAMES[worker] ?? worker.replace(/_/g, " ");
};

export const TOOL_LABELS: Record<string, string> = {
  search_handbook: "Searched the Employee Handbook",
  list_handbook_sections: "Listed handbook sections",
  get_user_info: "Looked up employee",
  get_user_department: "Looked up department",
  get_weather: "Checked the weather",
  calculator: "Used the calculator",
};
