import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** The boot splash shown while `/api/auth/me/` resolves on first load. */
@Component({
  selector: 'app-boot-screen',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="boot">
      <img class="mark" src="assets/brand/prolithica-panther.png" alt="Prolithica Technologies" width="319" height="343">
      <div class="track"><div class="bootbar"></div></div>
      <div class="step">{{ step() }}</div>
    </div>
  `,
  styles: [`
    .boot { position: fixed; inset: 0; z-index: 60; background: var(--pl-color-ffffff); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 34px; }
    .mark { display: block; width: min(200px, 55vw); height: auto; object-fit: contain; }
    .track { width: 220px; height: 2px; background: var(--pl-color-eeeeee); overflow: hidden; }
    .bootbar { width: 100%; height: 2px; background: var(--pl-color-3d3d3d); }
    .step { font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--pl-color-8a8a8a); }
  `],
})
export class BootScreenComponent {
  readonly step = input<string>('Connecting to Prolithica OS');
}
