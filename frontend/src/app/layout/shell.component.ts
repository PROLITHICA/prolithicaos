import { NotificationStateService } from '../core/notification-state.service';
import { ReportReminderComponent } from '../features/workspace/report-reminder.component';
import { PresenceService } from '../core/presence.service';
import { ThemeColorPipe } from '../shared/ui/theme-color.pipe';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  ActivatedRoute, NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router,
  RouterLink, RouterLinkActive, RouterOutlet,
} from '@angular/router';
import { filter } from 'rxjs';

import { ThemeService } from '../core/theme.service';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { LoadingService } from '../core/loading.service';
import { PageTitleService } from '../core/page-title.service';
import { Department, NavGroup } from '../core/models';
import { PermissionService } from '../core/permission.service';
import { BreadcrumbsComponent, Crumb } from '../shared/ui/breadcrumbs/breadcrumbs.component';
import { SkeletonComponent } from '../shared/ui/skeleton/skeleton.component';
import { ToastHostComponent } from '../shared/ui/toast-host/toast-host.component';

const HOME_ROUTES: Record<string, string> = {
  command: '/command', finance: '/finance', tech: '/tech', rnd: '/rnd', admin: '/admin-desk',
};

/** Sidebar + topbar + routed page. Every authenticated view lives inside it. */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [ThemeColorPipe, ReportReminderComponent,
    RouterOutlet, RouterLink, RouterLinkActive, FormsModule,
    BreadcrumbsComponent, SkeletonComponent, ToastHostComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.css',
})
export class ShellComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly auth = inject(AuthService);
  readonly perms = inject(PermissionService);
  readonly loader = inject(LoadingService);
  private readonly titles = inject(PageTitleService);

  readonly theme = inject(ThemeService);
  readonly departments = computed(() => this.user()?.visible_departments ?? []);
  readonly notifications = inject(NotificationStateService);
  readonly presence = inject(PresenceService);
  readonly notifCount = this.notifications.unread;
  private readonly routeTitle = signal<string>('');
  /** A screen may name itself; otherwise the route's own title stands. */
  readonly pageTitle = computed(() => this.titles.title() || this.routeTitle());
  readonly crumbs = signal<Crumb[]>([]);
  readonly crumbCurrent = signal<string>('');
  readonly query = signal<string>('');
  /** Off-canvas sidebar, used below the desk breakpoint. */
  readonly navOpen = signal(false);

  readonly user = this.auth.currentUser;
  readonly navGroups = computed<NavGroup[]>(() => this.perms.navGroups());
  readonly person = computed(() => this.user()?.display_name ?? '');
  readonly personTitle = computed(() => this.user()?.job_title ?? '');
  readonly initials = computed(() => this.user()?.initials ?? '');
  readonly activeDept = computed(() => this.user()?.department?.slug ?? '');

  constructor() {
    this.notifications.unread.set(0);
    this.notifications.refresh();

    this.router.events.pipe(filter((event) => event instanceof NavigationStart))
      .subscribe(() => this.loader.start('Loading records and permissions'));

    this.router.events
      .pipe(filter((event) =>
        event instanceof NavigationEnd || event instanceof NavigationCancel || event instanceof NavigationError))
      .subscribe(() => {
        this.loader.stop();
        this.closeNav();
        this.titles.clear();
        this.readRouteData();
      });

    this.readRouteData();
  }

  private readRouteData(): void {
    // Called once on construction as well as after every navigation, so the
    // deepest child may not have been activated — and therefore have no
    // snapshot — yet. Take the deepest route that actually carries one.
    let child = this.route;
    while (child.firstChild?.snapshot) child = child.firstChild;

    const data = (child.snapshot?.data ?? {}) as {
      title?: string;
      crumbs?: Crumb[];
      crumbCurrent?: string;
    };
    this.routeTitle.set(data.title ?? '');
    this.crumbs.set(data.crumbs ?? []);
    this.crumbCurrent.set(data.crumbCurrent ?? '');
  }

  toggleNav(): void {
    this.navOpen.update((open) => !open);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }

  departmentRoute(dept: Department): string {
    return HOME_ROUTES[dept.home_view] ?? `/${dept.home_view}`;
  }

  goSearch(): void {
    void this.router.navigate(['/search'], {
      queryParams: this.query() ? { q: this.query() } : {},
    });
  }

  signOut(): void {
    this.auth.logout();
  }
}
