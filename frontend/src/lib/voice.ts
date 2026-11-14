// Client for the Python Mobilize API (`voice-agents console`), which builds
// persona voice agents and places calls through ElevenLabs.
import type { Handoff } from './api';

export type AgentKind = 'legislator' | 'survey' | 'lobbyist' | 'generated';
export interface Persona { name: string; age: number; gender: string; age_band: string; occupation: string; background: string; personal_impact: string; voice_id: string; synthetic: boolean }
export interface VoiceAgent {
  id: string; kind: AgentKind; template: string; archetype?: string; caller: string; target: string;
  persona: Persona | null; voice_id: string; voice: string;
  request: { to_number: string; dynamic_variables: Record<string, string> };
  payload: Record<string, unknown> & { agent_id: string };
  created_at: string; conversations: string[];
}
export type Stage = 'input' | 'plan' | 'persona' | 'voice' | 'assemble' | 'ready';
export interface PipelineEvent { t: string; stage: Stage; status: 'running' | 'done' | 'error'; message: string; data?: Record<string, any>; agent?: VoiceAgent }
export interface VoiceStatus { elevenlabs_key: boolean; phone_number: boolean; allowed_numbers: string[]; persona_model: string; max_personas: number }
export interface DemoInput {
  to_number: string;
  policy: { title: string; summary: string; fiscal_impact: string; state: string; pain_point: string };
  legislator: { title: string; name: string; district: string };
  lobbyist: { name: string; firm: string; client_name: string };
  district_profile: string;
}
export interface Conversation {
  status: string; duration: number | null; summary: string | null;
  transcript: { role: string; message: string; at: number | null }[];
  data_collection: Record<string, unknown>; evaluation: Record<string, string>;
}

const base = (import.meta.env.VITE_VOICE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(base + path, init); } catch { throw new Error('Could not reach the Mobilize API. Start it with `voice-agents console`.'); }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : `Mobilize API failed (HTTP ${response.status}).`);
  return data as T;
}

export const getStatus = () => request<VoiceStatus>('/api/status');
export const getDemoInput = () => request<DemoInput>('/api/input');
export const listAgents = () => request<VoiceAgent[]>('/api/agents');
export const placeCall = (agentId: string) => request<{ conversation_id: string }>(`/api/agents/${encodeURIComponent(agentId)}/call`, { method: 'POST' });
export const getConversation = (id: string) => request<Conversation>(`/api/conversations/${encodeURIComponent(id)}`);

/** Run the pipeline, calling `onEvent` for each streamed trace event. */
export async function runPipeline(body: { personas: number; source: 'sample' | 'claude'; handoff: Handoff | null }, onEvent: (e: PipelineEvent) => void) {
  let response: Response;
  try {
    response = await fetch(base + '/api/pipeline', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  } catch { throw new Error('Could not reach the Mobilize API. Start it with `voice-agents console`.'); }
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Pipeline failed (HTTP ${response.status}).`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let ready = false;
  let pipelineError = '';
  const dispatch = (part: string) => {
    if (!part.startsWith('data: ')) return;
    const event: PipelineEvent = JSON.parse(part.slice(6));
    if (event.status === 'error') pipelineError = event.message;
    if (event.stage === 'ready' && event.status === 'done') ready = true;
    onEvent(event);
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const part of parts) dispatch(part);
  }
  buffer += decoder.decode();
  if (buffer.trim()) dispatch(buffer.trim());
  if (!ready) throw new Error(pipelineError || 'Agent build ended unexpectedly. Please try again.');
}
