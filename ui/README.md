# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## Testing

The Playwright suite (`tests_ui/`) exercises real, authenticated routes -- RLS is the actual
security boundary (anon has no `SELECT` grant on any reconciliation table), so the suite needs a
signed-in operator session, not just the anon key.

Set these two env vars before running `bun run test` / `bun x playwright test`:

```sh
export TEST_OPERATOR_EMAIL="you@example.com"
export TEST_OPERATOR_PASSWORD="..."
```

The account needs an `operator` (or `admin`) row in `public.user_roles` -- a fresh self-service
sign-up alone is not enough, since only `service_role` can write that table. To provision one:

1. Sign up normally via `/auth` (or the Supabase Auth REST `signup` endpoint) and confirm the
   email.
2. Have an existing admin (or run directly against the database, e.g. via the Supabase SQL editor)
   grant the role:
   ```sql
   insert into public.user_roles (user_id, role) values ('<the new user's id>', 'operator');
   ```

`tests_ui/global-setup.ts` signs this account in once per run via the real password grant and
seeds every test's browser storageState with the resulting session -- see `tests_ui/auth-helpers.ts`.

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS
