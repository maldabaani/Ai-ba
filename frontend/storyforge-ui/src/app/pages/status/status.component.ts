import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { StoryForgeJobState, StoryForgeService } from '../../services/storyforge.service';

const POLL_INTERVAL_MS = 3000;

const STEPS = ['analyzing', 'clarifying', 'generating', 'reviewing', 'creating', 'done'] as const;

@Component({
  selector: 'app-status',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './status.component.html',
  styleUrl: './status.component.css',
})
export class StatusComponent implements OnInit, OnDestroy {
  jobId = '';
  state: StoryForgeJobState | null = null;
  loadError = '';

  readonly steps = STEPS;

  private pollHandle: ReturnType<typeof setInterval> | null = null;
  private redirected = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private storyForgeService: StoryForgeService
  ) {}

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') ?? '';
    this.poll();
    this.pollHandle = setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  ngOnDestroy(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
    }
  }

  private poll(): void {
    if (this.redirected) {
      return;
    }

    this.storyForgeService.getAssessmentStatus(this.jobId).subscribe({
      next: (state) => {
        this.state = state;

        if (state.status === 'clarifying') {
          this.redirectOnce(['/clarify', this.jobId]);
        } else if (state.status === 'reviewing' && state.review_mode) {
          this.redirectOnce(['/review', this.jobId]);
        } else if (state.status === 'done' || state.status === 'error') {
          this.stopPolling();
        }
      },
      error: () => {
        this.loadError = 'Unable to load job status.';
        this.stopPolling();
      },
    });
  }

  private redirectOnce(commands: (string | number)[]): void {
    if (this.redirected) {
      return;
    }
    this.redirected = true;
    this.stopPolling();
    this.router.navigate(commands);
  }

  private stopPolling(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  stepClass(step: string): string {
    if (!this.state) {
      return 'sf-step';
    }
    const currentIndex = this.steps.indexOf(this.state.status as (typeof STEPS)[number]);
    const stepIndex = this.steps.indexOf(step as (typeof STEPS)[number]);

    if (this.state.status === 'error') {
      return 'sf-step';
    }
    if (stepIndex < currentIndex || this.state.status === 'done') {
      return 'sf-step sf-step-done';
    }
    if (stepIndex === currentIndex) {
      return 'sf-step sf-step-active';
    }
    return 'sf-step';
  }
}
