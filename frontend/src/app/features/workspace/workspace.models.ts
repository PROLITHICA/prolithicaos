export interface Choice { id: string; label?: string; name?: string; display_name?: string; employee_number?: string; }
export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'done';
export interface WorkTask { id: string; text: string; done: boolean; status: TaskStatus; priority: string; due_date: string | null; project: string; project_id: string; assignee_id: string; assignee: string; department: string | null; can_complete: boolean; }
export interface Page<T> { count: number; page: number; has_next: boolean; results: T[]; }
export interface Report { id: string; user_id: string; person: string; department: string; date: string; completed: string; tomorrow: string; blockers: string; updated_at: string; tasks: { id: string; text: string }[]; }
export interface ReportPage extends Page<Report> { submitted: number; expected: number; missing: Choice[]; blocker_count: number; date: string; own_report: Report | null; reminder: boolean; can_manage: boolean; departments: Choice[]; }
export interface ChatMember { id: string; name: string; admin: boolean; }
export interface ChatThread { id: string; name: string; direct: boolean; department: string | null; archived: boolean; can_manage: boolean; can_pin: boolean; members: ChatMember[]; }
export interface ChatMessage { id: string; body: string; author: string; created_at: string; mine: boolean; pinned: boolean; attachment_name: string; attachment_url: string | null; }
export interface MessagePage extends Page<ChatMessage> { archived: boolean; can_pin: boolean; }
export function nairobiDate(): string {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Africa/Nairobi', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  const part = (type: string) => parts.find(p => p.type === type)?.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}
export function errorMessage(error: { error?: unknown }): string {
  const detail = error.error;
  if (detail && typeof detail === 'object') return Object.entries(detail).map(([key, value]) => `${key === 'detail' || key === 'non_field_errors' ? '' : key + ': '}${Array.isArray(value) ? value.join(' ') : String(value)}`).join(' ');
  return 'Could not connect. Please try again.';
}
