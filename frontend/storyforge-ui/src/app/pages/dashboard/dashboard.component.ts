import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { JobSummary, StoryForgeService } from '../../services/storyforge.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  jobs: JobSummary[] = [];
  loading = true;
  loadError = '';
  rerunningId = '';

  constructor(
    private storyForgeService: StoryForgeService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadJobs();
  }

  loadJobs(): void {
    this.loading = true;
    this.storyForgeService.listJobs().subscribe({
      next: (jobs) => {
        this.jobs = jobs;
        this.loading = false;
      },
      error: () => {
        this.loadError = 'Unable to load assessment jobs.';
        this.loading = false;
      },
    });
  }

  rerun(jobId: string): void {
    this.rerunningId = jobId;
    this.storyForgeService.rerunAssessment(jobId).subscribe({
      next: ({ job_id }) => {
        this.rerunningId = '';
        this.router.navigate(['/status', job_id]);
      },
      error: () => {
        this.rerunningId = '';
      },
    });
  }

  badgeClass(status: string): string {
    return `sf-badge sf-badge-${status}`;
  }

  relativeTime(epochSeconds: number): string {
    const diff = Date.now() - epochSeconds * 1000;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  fullDate(epochSeconds: number): string {
    return new Date(epochSeconds * 1000).toLocaleString();
  }
}
