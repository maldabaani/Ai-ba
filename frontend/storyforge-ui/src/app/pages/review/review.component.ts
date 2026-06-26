import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { GeneratedStory, StoryForgeService } from '../../services/storyforge.service';

@Component({
  selector: 'app-review',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './review.component.html',
  styleUrl: './review.component.css',
})
export class ReviewComponent implements OnInit {
  jobId = '';
  stories: GeneratedStory[] = [];
  expandedIndex: number | null = 0;

  loading = true;
  submitting = false;
  loadError = '';
  submitError = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private storyForgeService: StoryForgeService
  ) {}

  ngOnInit(): void {
    this.jobId = this.route.snapshot.paramMap.get('jobId') ?? '';
    this.loadStories();
  }

  loadStories(): void {
    this.loading = true;
    this.storyForgeService.getAssessmentStatus(this.jobId).subscribe({
      next: (state) => {
        this.stories = structuredClone(state.generated_stories);
        this.loading = false;
      },
      error: () => {
        this.loadError = 'Unable to load generated stories.';
        this.loading = false;
      },
    });
  }

  toggleExpanded(index: number): void {
    this.expandedIndex = this.expandedIndex === index ? null : index;
  }

  approve(): void {
    this.submitting = true;
    this.submitError = '';

    this.storyForgeService.approveReview(this.jobId, this.stories).subscribe({
      next: () => {
        this.router.navigate(['/status', this.jobId]);
      },
      error: () => {
        this.submitting = false;
        this.submitError = 'Failed to approve stories. Please try again.';
      },
    });
  }
}
