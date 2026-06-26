import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';

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

  constructor(private storyForgeService: StoryForgeService) {}

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

  badgeClass(status: string): string {
    return `sf-badge sf-badge-${status}`;
  }

  formatDate(epochSeconds: number): string {
    return new Date(epochSeconds * 1000).toLocaleString();
  }
}
