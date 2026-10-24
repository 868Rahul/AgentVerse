import React from "react";
import { Segmented } from "antd";
import { AGENTS, getAgent } from "../agents";

interface AgentSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const AgentSelector: React.FC<AgentSelectorProps> = ({ value, onChange }) => (
  <div className="flex items-center gap-3 min-w-0">
    <Segmented
      value={value}
      onChange={(v) => onChange(v as string)}
      options={AGENTS.map((agent) => ({
        value: agent.id,
        label: (
          <span className="flex items-center gap-2 px-1" title={agent.tagline}>
            {agent.icon}
            <span className="hidden md:inline">{agent.name}</span>
            <span className="md:hidden">{agent.shortName}</span>
          </span>
        ),
      }))}
    />
    <span className="hidden xl:inline text-sm text-slate-400 truncate">{getAgent(value).tagline}</span>
  </div>
);

export default AgentSelector;
