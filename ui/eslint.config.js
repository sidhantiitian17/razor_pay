import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    // Generated/frozen files, never hand-edited or auto-fixed:
    // src/integrations/supabase/** is Lovable-generated ("do not edit
    // directly") boilerplate scaffolded by enable_database. src/types/
    // report.d.ts is the frozen contract regenerated from
    // contracts/report.schema.json (CI diffs it against a fresh
    // regeneration -- see ci.yml "Report types match frozen schema";
    // ESLint --fix previously stripped its header comment because the
    // file has zero violations to justify it, which is exactly why it
    // must stay out of lint's reach entirely).
    ignores: ["dist", ".output", ".vinxi", "src/integrations/supabase/**", "src/types/report.d.ts"],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "server-only",
              message:
                "TanStack Start does not use the Next.js `server-only` package. Rename the module to `*.server.ts` or mark it with `@tanstack/react-start/server-only`.",
            },
          ],
        },
      ],
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  eslintPluginPrettier,
);
