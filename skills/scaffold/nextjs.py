"""Next.js project scaffolding skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class ScaffoldNextJS(BaseSkill):
    """Scaffold a new Next.js project with App Router."""

    @property
    def name(self) -> str:
        return "scaffold_nextjs"

    @property
    def slash_command(self) -> str:
        return "/scaffold-nextjs"

    @property
    def description(self) -> str:
        return "Create a new Next.js project with App Router, TypeScript, and modern tooling"

    @property
    def category(self) -> str:
        return "scaffold"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_name",
                "type": "string",
                "description": "Name of the project to create",
                "required": True,
            },
            {
                "name": "database",
                "type": "string",
                "description": "Database: prisma, drizzle, or none",
                "required": False,
            },
            {
                "name": "auth",
                "type": "string",
                "description": "Authentication: next-auth, clerk, or none",
                "required": False,
            },
            {
                "name": "styling",
                "type": "string",
                "description": "Styling: tailwind, shadcn, or css-modules",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        project_name = kwargs.get("project_name", "my-nextjs-app")
        database = kwargs.get("database", "prisma")
        auth = kwargs.get("auth", "next-auth")
        styling = kwargs.get("styling", "shadcn")

        guidance = f"""# Next.js Project Scaffolding Guide

## Project: {project_name}

### Step 1: Create Next.js Project
```bash
npx create-next-app@latest {project_name} --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd {project_name}
```

### Step 2: Install Additional Dependencies
"""

        # Styling
        if styling == "shadcn":
            guidance += """
#### shadcn/ui Components
```bash
npx shadcn@latest init
```

Choose these options:
- Style: Default
- Base color: Slate
- CSS variables: Yes

Install common components:
```bash
npx shadcn@latest add button card input form dialog toast
```
"""

        # Database
        if database == "prisma":
            guidance += """
#### Prisma ORM
```bash
npm install prisma @prisma/client
npx prisma init
```

Example schema (`prisma/schema.prisma`):
```prisma
generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "postgresql"
  url      = env("DATABASE_URL")
}}

model User {{
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}}
```

Create Prisma client (`src/lib/prisma.ts`):
```typescript
import {{ PrismaClient }} from '@prisma/client'

const globalForPrisma = globalThis as unknown as {{
  prisma: PrismaClient | undefined
}}

export const prisma = globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
```
"""
        elif database == "drizzle":
            guidance += """
#### Drizzle ORM
```bash
npm install drizzle-orm postgres
npm install -D drizzle-kit
```

Create config (`drizzle.config.ts`):
```typescript
import {{ defineConfig }} from 'drizzle-kit'

export default defineConfig({{
  schema: './src/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {{
    url: process.env.DATABASE_URL!,
  }},
}})
```
"""

        # Auth
        if auth == "next-auth":
            guidance += """
#### NextAuth.js (Auth.js)
```bash
npm install next-auth@beta
```

Create auth config (`src/auth.ts`):
```typescript
import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"

export const {{ handlers, signIn, signOut, auth }} = NextAuth({{
  providers: [GitHub],
}})
```

Add route handler (`src/app/api/auth/[...nextauth]/route.ts`):
```typescript
import {{ handlers }} from "@/auth"
export const {{ GET, POST }} = handlers
```
"""
        elif auth == "clerk":
            guidance += """
#### Clerk Authentication
```bash
npm install @clerk/nextjs
```

Update `middleware.ts`:
```typescript
import {{ clerkMiddleware }} from '@clerk/nextjs/server'

export default clerkMiddleware()

export const config = {{
  matcher: ['/((?!.*\\\\..*|_next).*)', '/', '/(api|trpc)(.*)'],
}}
```
"""

        guidance += f"""
### Step 3: Project Structure
```
{project_name}/
├── src/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── (auth)/           # Auth route group
│   │   ├── dashboard/        # Dashboard pages
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home page
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/               # shadcn components
│   │   └── ...               # Custom components
│   ├── lib/
│   │   ├── prisma.ts         # Database client
│   │   └── utils.ts          # Utility functions
│   └── types/
├── prisma/
│   └── schema.prisma
├── public/
├── .env.local
├── next.config.js
└── package.json
```

### Step 4: Environment Variables
Create `.env.local`:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
NEXTAUTH_SECRET="your-secret-key"
NEXTAUTH_URL="http://localhost:3000"
```

### Step 5: Development
```bash
npm run dev
```

### Recommended Additions
- Zod for validation
- TanStack Query for data fetching
- Server Actions for mutations
- Middleware for auth protection
"""

        return {
            "guidance": guidance,
            "context": {
                "project_name": project_name,
                "database": database,
                "auth": auth,
                "styling": styling,
            },
            "success": True,
        }
