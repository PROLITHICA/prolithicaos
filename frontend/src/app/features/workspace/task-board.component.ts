import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { ApiService } from '../../core/api.service';
import { Choice, Page, WorkTask, TaskStatus, errorMessage, nairobiDate } from './workspace.models';

@Component({ selector: 'app-task-board', standalone: true, imports: [FormsModule, DatePipe], templateUrl: './task-board.component.html', styleUrl: './task-board.css' })
export class TaskBoardComponent implements OnInit {
  @Input() projects: Choice[] = [];
  @Input() people: Choice[] = [];
  @Input() departments: Choice[] = [];
  @Input() canAssign = false;
  api = inject(ApiService);
  tasks = signal<WorkTask[]>([]); count = signal(0); hasNext = signal(false); loading = signal(false); busy = signal(false); error = signal(''); notice = signal('');
  private generation = 0;
  view: 'board' | 'list' = 'board'; page = 1; dragged: WorkTask | null = null;
  filters = { department: '', project: '', assignee: '', priority: '', due_before: '', q: '' };
  columns: { value: TaskStatus; label: string }[] = [{ value: 'todo', label: 'To do' }, { value: 'in_progress', label: 'In progress' }, { value: 'blocked', label: 'Blocked' }, { value: 'done', label: 'Done' }];
  priorities = ['low', 'normal', 'high', 'urgent'];
  ngOnInit() { this.load(); }
  load(append = false) {
    this.loading.set(true); this.error.set('');
    if (!append) this.page = 1;
    const page = this.page; const generation = ++this.generation;
    this.api.get<Page<WorkTask>>('/workspace/tasks/', { ...this.filters, page }).subscribe({ next: data => {
      if (generation !== this.generation) return;
      this.tasks.set(append ? [...this.tasks(), ...data.results] : data.results); this.count.set(data.count); this.hasNext.set(data.has_next); this.loading.set(false);
    }, error: e => { if (generation !== this.generation) return; if (append) this.page--; this.loading.set(false); this.error.set(errorMessage(e)); } });
  }
  more() { if (this.loading()) return; this.page++; this.load(true); }
  inColumn(status: TaskStatus) { return this.tasks().filter(task => task.status === status); }
  overdue(task: WorkTask) { return !!task.due_date && task.due_date < nairobiDate() && !task.done; }
  update(task: WorkTask, changes: Record<string, unknown>) {
    if (this.busy() || this.loading()) return;
    this.generation++; this.loading.set(false); this.busy.set(true); this.error.set(''); this.notice.set('');
    this.api.patch<WorkTask>('/workspace/tasks/' + task.id + '/', changes).subscribe({ next: updated => {
      this.busy.set(false); this.tasks.update(tasks => tasks.map(t => t.id === task.id ? updated : t)); this.notice.set('Task updated.'); this.load();
    }, error: e => { this.busy.set(false); this.error.set(errorMessage(e)); } });
  }
  drag(event: DragEvent, task: WorkTask) { if (!task.can_complete || this.busy() || this.loading()) { event.preventDefault(); return; } this.dragged = task; event.dataTransfer?.setData('text/plain', task.id); }
  drop(event: DragEvent, status: TaskStatus) { event.preventDefault(); if (this.dragged && this.dragged.status !== status) this.update(this.dragged, { status }); this.dragged = null; }
}
