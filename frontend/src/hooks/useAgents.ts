import { useQuery } from "@tanstack/react-query";
import { fetchAgentLogs, fetchAgents, type AgentLogFilters } from "../api/agents";

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
  });
}

export function useAgentLogs(filters: AgentLogFilters = {}) {
  return useQuery({
    queryKey: ["agent-logs", filters],
    queryFn: () => fetchAgentLogs(filters),
  });
}
