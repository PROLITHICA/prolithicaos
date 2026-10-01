import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { Page, WorkTask, ReportPage, errorMessage, nairobiDate } from './workspace.models';

@Component({ selector: 'app-daily-reports', standalone: true, imports: [FormsModule, DatePipe, RouterLink], templateUrl: './reports.component.html', styleUrl: './reports.css' })
export class ReportsComponent implements OnInit {
  @Input() embedded = false;
  api = inject(ApiService); data = signal<ReportPage | null>(null); error = signal(''); notice = signal(''); busy = signal(false); loading = signal(false);
  taskOptions = signal<WorkTask[]>([]); taskHasNext = signal(false); taskPage = 1; taskLoading = signal(false);
  today = nairobiDate(); date = this.today; department = ''; page = 1; private generation = 0; private draftDate = '';
  draft = { completed: '', tomorrow: '', blockers: '', tasks: [] as string[] };
  ngOnInit() { this.load(); this.loadTasks(); }
  load(append = false, resetDraft = true) {
    if (!append) this.page = 1;
    const generation = ++this.generation; this.loading.set(true); this.error.set('');
    this.api.get<ReportPage>('/workspace/reports/', { date: this.date, department: this.department, page: this.page }).subscribe({ next: response => {
      if (generation !== this.generation) return;
      this.loading.set(false); this.data.set(append && this.data() ? { ...response, results: [...this.data()!.results, ...response.results] } : response);
      if (!append && (resetDraft || this.draftDate !== response.date)) { this.draftDate = response.date; const own = response.own_report; this.draft = { completed: own?.completed ?? '', tomorrow: own?.tomorrow ?? '', blockers: own?.blockers ?? '', tasks: own?.tasks.map(t => t.id) ?? [] }; }
    }, error: e => { if (generation !== this.generation) return; if (append) this.page--; this.loading.set(false); this.error.set(errorMessage(e)); } });
  }
  loadTasks(append = false) {
    if (this.taskLoading()) return; this.taskLoading.set(true);
    if (append) this.taskPage++;
    this.api.get<Page<WorkTask>>('/workspace/tasks/', { page: this.taskPage }).subscribe({ next: response => {
      this.taskLoading.set(false); this.taskOptions.set(append ? [...this.taskOptions(), ...response.results] : response.results); this.taskHasNext.set(response.has_next);
    }, error: e => { this.taskLoading.set(false); if (append) this.taskPage--; this.error.set(errorMessage(e)); } });
  }
  more() { if (this.loading()) return; this.page++; this.load(true, false); }
  save() {
    if (this.busy()) return;
    if (this.loading() || !this.data() || this.data()!.date !== this.date || this.draftDate !== this.date) { this.error.set('Load the selected report date before saving.'); return; }
    this.busy.set(true); this.error.set(''); this.notice.set('');
    this.api.post('/workspace/reports/', { ...this.draft, date: this.date }).subscribe({ next: () => {
      this.busy.set(false); this.notice.set('Your daily report is saved.'); window.dispatchEvent(new Event('prolithica:report-saved')); this.load(false, false);
    }, error: e => { this.busy.set(false); this.error.set(errorMessage(e)); } });
  }
  toggleTask(id: string, checked: boolean) { this.draft.tasks = checked ? [...new Set([...this.draft.tasks, id])] : this.draft.tasks.filter(t => t !== id); }
}
