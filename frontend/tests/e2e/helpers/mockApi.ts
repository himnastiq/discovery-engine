import type { Page } from '@playwright/test';
import typesFixture from '../../fixtures/types.json' with { type: 'json' };
import usersFixture from '../../fixtures/users_movies.json' with { type: 'json' };
import profileFixture from '../../fixtures/profile_movies_1.json' with { type: 'json' };
import recommendFixture from '../../fixtures/recommend_movies_1.json' with { type: 'json' };
import metricsFixture from '../../fixtures/metrics_movies.json' with { type: 'json' };
import aboutFixture from '../../fixtures/about.json' with { type: 'json' };
import chatStatusFixture from '../../fixtures/chat_status.json' with { type: 'json' };
import chatResponseFixture from '../../fixtures/chat_response.json' with { type: 'json' };

export async function setupMockApi(page: Page) {
  // Chat endpoints (Phase 13)
  await page.route('**/api/chat', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(chatResponseFixture),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(chatStatusFixture),
      });
    }
  });

  // Types endpoint
  await page.route('**/api/types', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(typesFixture),
    });
  });

  // Users endpoint
  await page.route('**/api/types/*/users*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(usersFixture),
    });
  });

  // User Profile endpoint
  await page.route('**/api/types/*/users/*/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(profileFixture),
    });
  });

  // Recommendations endpoint
  await page.route('**/api/types/*/recommend*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(recommendFixture),
    });
  });

  // Popular endpoint
  await page.route('**/api/types/*/popular*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(recommendFixture),
    });
  });

  // Similar endpoint
  await page.route('**/api/types/*/similar*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(recommendFixture),
    });
  });

  // Item detail endpoint
  await page.route('**/api/types/*/items/*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        item_id: '385',
        title: 'The Matrix (1999)',
        categories: ['Action', 'Sci-Fi'],
        year: 1999,
        text: 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
        popularity_rank: 1,
        meta: {},
      }),
    });
  });

  // Search items endpoint
  await page.route('**/api/types/*/search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        content_type: 'movies',
        query: 'matrix',
        total_matches: 1,
        results: [
          {
            item_id: '385',
            title: 'The Matrix (1999)',
            categories: ['Action', 'Sci-Fi'],
            year: 1999,
            popularity_rank: 1,
          },
        ],
      }),
    });
  });

  // Cold start endpoint
  await page.route('**/api/recommend/cold-start*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(recommendFixture),
    });
  });

  // Metrics endpoint
  await page.route('**/api/types/*/metrics*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(metricsFixture),
    });
  });

  // About endpoint
  await page.route('**/api/about*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(aboutFixture),
    });
  });
}
