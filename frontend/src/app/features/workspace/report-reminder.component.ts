import { Component, OnDestroy, inject, signal, DestroyRef } from '@angular/core';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { ReportPage } from './workspace.models';

@Component({ selector: 'app-report-reminder', standalone: true, imports: [RouterLink], template: `@if(due()){<aside class="daily-reminder" aria-label="Daily report reminder"><span><strong>Before you wrap up.</strong> Share today's work and any blockers with your team.</span><a routerLink="/reports">Write my report →</a></aside>}`, styles: [`.daily-reminder{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 20px;margin-bottom:24px;background:var(--pl-pane-sunken);border:1px solid var(--pl-hairline);border-radius:16px;font-size:13px;color:var(--pl-ink)}a{white-space:nowrap;color:inherit;font-weight:500}@media(max-width:650px){.daily-reminder{align-items:flex-start;flex-direction:column}}`] })
export class ReportReminderComponent implements OnDestroy {
  api = inject(ApiService); auth = inject(AuthService); destroyRef = inject(DestroyRef); due = signal(false);
  private refresh = () => {
    const role = this.auth.currentUser()?.role?.slug;
    if (role === 'client' || role === 'client_portal') return;
    this.api.get<ReportPage>('/workspace/reports/').pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: data => this.due.set(data.reminder), error: () => this.due.set(false) });
  };
  timer = window.setInterval(this.refresh, 60000);
  constructor() { this.refresh(); window.addEventListener('prolithica:report-saved', this.refresh); }
  ngOnDestroy() { clearInterval(this.timer); window.removeEventListener('prolithica:report-saved', this.refresh); }
}
