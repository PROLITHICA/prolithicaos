import { Component, inject, signal, OnDestroy, DestroyRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiService } from '../../core/api.service';
import { ChatMessage, ChatThread, Choice, MessagePage, errorMessage } from './workspace.models';
@Component({ selector: 'app-chat', standalone: true, imports: [FormsModule, DatePipe], templateUrl: './chat.component.html', styleUrl: './chat.css' })
export class ChatComponent implements OnDestroy {
  api = inject(ApiService); destroyRef = inject(DestroyRef);
  threads = signal<ChatThread[]>([]); people = signal<Choice[]>([]); messages = signal<ChatMessage[]>([]); selected = signal<ChatThread | null>(null);
  error = signal(''); busy = signal(false); ready = signal(false); reading = signal(false); downloading = signal(false); hasNext = signal(false); count = signal(0);
  draft = ''; name = ''; members: string[] = []; direct = true; groupMembers: string[] = []; groupName = '';
  search = ''; pinnedOnly = false; page = 1; file: File | null = null; showArchived = false; private generation = 0;
  timer = window.setInterval(() => { this.load(); if (this.selected() && this.page === 1 && !this.reading()) this.read(false, false); }, 8000);
  constructor() { this.load(); }
  ngOnDestroy() { clearInterval(this.timer); }
  fail(error: { error?: unknown }, operation: 'read' | 'write' | 'download' | 'list' = 'write') {
    if (operation === 'write') this.busy.set(false);
    if (operation === 'read') this.reading.set(false);
    if (operation === 'download') this.downloading.set(false);
    this.error.set(errorMessage(error));
  }
  load() {
    this.api.get<{ threads: ChatThread[]; people: Choice[] }>('/workspace/threads/').pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: data => {
      this.threads.set(data.threads); this.people.set(data.people); this.ready.set(true);
      const active = this.selected();
      if (active) { const fresh = data.threads.find(t => t.id === active.id); this.selected.set(fresh ?? null); if (!fresh) { this.generation++; this.messages.set([]); } }
    }, error: e => this.fail(e, 'list') });
  }
  visibleThreads() { return this.threads().filter(t => this.showArchived || !t.archived); }
  select(thread: ChatThread) {
    if (this.busy()) return;
    this.groupName = thread.name; this.groupMembers = thread.members.filter(m => !m.admin).map(m => m.id);
    this.selected.set(thread); this.messages.set([]); this.error.set(''); this.search = ''; this.pinnedOnly = false; this.page = 1; this.draft = ''; this.file = null; this.generation++; this.read();
  }
  read(append = false, clearError = true) {
    const thread = this.selected(); if (!thread) return;
    const generation = ++this.generation; const page = this.page;
    this.reading.set(true); if (clearError) this.error.set('');
    this.api.get<MessagePage>('/workspace/threads/' + thread.id + '/messages/', { page, q: this.search, pinned: this.pinnedOnly ? 'true' : '' }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: response => {
      if (generation !== this.generation || this.selected()?.id !== thread.id) return;
      this.reading.set(false); this.count.set(response.count); this.hasNext.set(response.has_next);
      if (append) { const ids = new Set(this.messages().map(m => m.id)); this.messages.set([...response.results.filter(m => !ids.has(m.id)), ...this.messages()]); }
      else this.messages.set(response.results);
      this.selected.update(t => t ? { ...t, archived: response.archived, can_pin: response.can_pin } : t);
    }, error: e => { if (generation === this.generation) { if (append) this.page--; this.fail(e, 'read'); } } });
  }
  searchHistory() { this.page = 1; this.read(); }
  older() { if (this.reading()) return; this.page++; this.read(true); }
  create() {
    if (this.busy()) return; this.busy.set(true); this.error.set('');
    this.api.post<{ id: string }>('/workspace/threads/', { name: this.name, members: this.members, direct: this.direct }).subscribe({ next: result => {
      this.api.get<{ threads: ChatThread[]; people: Choice[] }>('/workspace/threads/').subscribe({ next: data => {
        this.busy.set(false); this.threads.set(data.threads); const thread = data.threads.find(t => t.id === result.id); if (thread) this.select(thread);
      }, error: e => this.fail(e) }); this.name = ''; this.members = [];
    }, error: e => this.fail(e) });
  }
  manage() {
    const thread = this.selected(); if (!thread || this.busy()) return; this.busy.set(true); this.error.set('');
    this.api.patch('/workspace/threads/' + thread.id + '/messages/', { name: this.groupName, members: this.groupMembers }).subscribe({ next: () => { this.busy.set(false); this.load(); }, error: e => this.fail(e) });
  }
  archive() {
    const thread = this.selected(); if (!thread || this.busy()) return; this.busy.set(true); this.error.set('');
    this.api.patch('/workspace/threads/' + thread.id + '/messages/', { archived: !thread.archived }).subscribe({ next: () => { this.busy.set(false); this.load(); this.read(); }, error: e => this.fail(e) });
  }
  attach(event: Event) { this.file = (event.target as HTMLInputElement).files?.[0] ?? null; if (this.file && this.file.size > 10 * 1024 * 1024) { this.error.set('Attachments must be 10 MB or smaller.'); this.file = null; (event.target as HTMLInputElement).value = ''; } }
  send(fileInput: HTMLInputElement) {
    const thread = this.selected(); if (!thread || thread.archived || this.busy() || (!this.draft.trim() && !this.file)) return;
    this.busy.set(true); this.error.set(''); const path = '/workspace/threads/' + thread.id + '/messages/';
    const request = this.file ? this.api.upload(path, this.file, { body: this.draft }) : this.api.post(path, { body: this.draft });
    request.subscribe({ next: () => {
      this.busy.set(false); if (this.selected()?.id !== thread.id) return; this.draft = ''; this.file = null; fileInput.value = ''; this.search = ''; this.pinnedOnly = false; this.page = 1; this.read();
    }, error: e => this.fail(e) });
  }
  pin(message: ChatMessage) {
    if (this.busy()) return; this.busy.set(true); this.error.set('');
    this.api.patch('/workspace/messages/' + message.id + '/', { pinned: !message.pinned }).subscribe({ next: () => { this.busy.set(false); this.page = 1; this.read(); }, error: e => this.fail(e) });
  }
  download(message: ChatMessage) {
    if (!message.attachment_url || this.downloading()) return; this.downloading.set(true); this.error.set('');
    this.api.downloadEvents(message.attachment_url).subscribe({ next: event => {
      if (event.type === HttpEventType.Response && event.body) {
        const url = URL.createObjectURL(event.body); const link = document.createElement('a'); link.href = url; link.download = message.attachment_name; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); this.downloading.set(false);
      }
    }, error: e => this.fail(e, 'download') });
  }
}
