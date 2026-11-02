import { http, HttpResponse } from 'msw';
import typesFixture from '../fixtures/types.json';
import usersMoviesFixture from '../fixtures/users_movies.json';
import profileMovies1Fixture from '../fixtures/profile_movies_1.json';
import recommendMovies1Fixture from '../fixtures/recommend_movies_1.json';
import aboutFixture from '../fixtures/about.json';
import chatStatusFixture from '../fixtures/chat_status.json';
import chatResponseFixture from '../fixtures/chat_response.json';

export const handlers = [
  http.get('/api/chat', () => {
    return HttpResponse.json(chatStatusFixture);
  }),

  http.post('/api/chat', () => {
    return HttpResponse.json(chatResponseFixture);
  }),

  http.get('/api/types', () => {
    return HttpResponse.json(typesFixture);
  }),

  http.get('/api/types/:type/users', ({ params }) => {
    const { type } = params;
    if (type === 'movies') {
      return HttpResponse.json(usersMoviesFixture);
    }
    return HttpResponse.json({
      content_type: String(type),
      total: 0,
      users: [],
    });
  }),

  http.get('/api/types/:type/users/:userId/profile', ({ params }) => {
    const { type, userId } = params;
    if (type === 'movies' && userId === '1') {
      return HttpResponse.json(profileMovies1Fixture);
    }
    return HttpResponse.json(
      {
        error: {
          code: 'USER_NOT_FOUND',
          message: `User ${userId} not found in domain ${type}`,
        },
      },
      { status: 404 }
    );
  }),

  http.get('/api/types/:type/recommend', () => {
    return HttpResponse.json(recommendMovies1Fixture);
  }),

  http.get('/api/types/:type/popular', () => {
    return HttpResponse.json(recommendMovies1Fixture);
  }),

  http.get('/api/types/:type/similar', () => {
    return HttpResponse.json(recommendMovies1Fixture);
  }),

  http.get('/api/about', () => {
    return HttpResponse.json(aboutFixture);
  }),
];

