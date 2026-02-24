# Project Memory

## Architecture
- Express.js backend with TypeScript
- PostgreSQL database via Prisma ORM
- React frontend with Next.js 15
- Auth: JWT tokens in httpOnly cookies (NOT Bearer headers)

## Past Mistakes
- 2024-12: Token expiry edge case caused 500 errors in production. Always validate both `exp` AND `iat` claims.
- 2025-01: Migration test was flaky because it depended on database ordering. Use explicit ORDER BY.
- 2025-03: API pagination broke when page size was 0. Always validate pagination params (min 1, max 100).

## Conventions
- All API responses use `{ data, error, meta }` envelope
- Database queries use Prisma, never raw SQL
- Tests must cover both success and error paths
- Imports: always absolute paths from `@/`
