"""Express.js project scaffolding skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class ScaffoldExpress(BaseSkill):
    """Scaffold a new Express.js project with TypeScript."""

    @property
    def name(self) -> str:
        return "scaffold_express"

    @property
    def slash_command(self) -> str:
        return "/scaffold-express"

    @property
    def description(self) -> str:
        return "Create a new Express.js project with TypeScript and modern tooling"

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
                "description": "Database: prisma, typeorm, drizzle, or none",
                "required": False,
            },
            {
                "name": "auth",
                "type": "string",
                "description": "Authentication: jwt, passport, or none",
                "required": False,
            },
            {
                "name": "validation",
                "type": "string",
                "description": "Validation: zod, joi, or class-validator",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        project_name = kwargs.get("project_name", "my-express-app")
        database = kwargs.get("database", "prisma")
        auth = kwargs.get("auth", "jwt")
        validation = kwargs.get("validation", "zod")

        guidance = f"""# Express.js Project Scaffolding Guide

## Project: {project_name}

### Step 1: Initialize Project
```bash
mkdir {project_name}
cd {project_name}
npm init -y
```

### Step 2: Install Core Dependencies
```bash
npm install express cors helmet morgan dotenv
npm install -D typescript @types/node @types/express @types/cors @types/morgan ts-node tsx nodemon
```

### Step 3: TypeScript Configuration
Create `tsconfig.json`:
```json
{{
  "compilerOptions": {{
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": "./src",
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "baseUrl": ".",
    "paths": {{
      "@/*": ["src/*"]
    }}
  }},
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}}
```

### Step 4: Install Additional Dependencies
"""

        # Validation
        if validation == "zod":
            guidance += """
#### Zod Validation
```bash
npm install zod
```

Example schema (`src/schemas/user.schema.ts`):
```typescript
import {{ z }} from 'zod'

export const createUserSchema = z.object({{
  body: z.object({{
    email: z.string().email(),
    password: z.string().min(8),
    name: z.string().optional(),
  }}),
}})

export type CreateUserInput = z.infer<typeof createUserSchema>['body']
```

Validation middleware (`src/middleware/validate.ts`):
```typescript
import {{ Request, Response, NextFunction }} from 'express'
import {{ AnyZodObject, ZodError }} from 'zod'

export const validate = (schema: AnyZodObject) =>
  async (req: Request, res: Response, next: NextFunction) => {{
    try {{
      await schema.parseAsync({{
        body: req.body,
        query: req.query,
        params: req.params,
      }})
      return next()
    }} catch (error) {{
      if (error instanceof ZodError) {{
        return res.status(400).json({{ errors: error.errors }})
      }}
      return next(error)
    }}
  }}
```
"""
        elif validation == "joi":
            guidance += """
#### Joi Validation
```bash
npm install joi
npm install -D @types/joi
```
"""
        elif validation == "class-validator":
            guidance += """
#### Class Validator
```bash
npm install class-validator class-transformer reflect-metadata
```
"""

        # Database
        if database == "prisma":
            guidance += """
#### Prisma ORM
```bash
npm install @prisma/client
npm install -D prisma
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
  password  String
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}}
```

Prisma client (`src/lib/prisma.ts`):
```typescript
import {{ PrismaClient }} from '@prisma/client'

export const prisma = new PrismaClient()
```
"""
        elif database == "typeorm":
            guidance += """
#### TypeORM
```bash
npm install typeorm reflect-metadata pg
npm install -D @types/node
```
"""
        elif database == "drizzle":
            guidance += """
#### Drizzle ORM
```bash
npm install drizzle-orm postgres
npm install -D drizzle-kit
```
"""

        # Auth
        if auth == "jwt":
            guidance += """
#### JWT Authentication
```bash
npm install jsonwebtoken bcryptjs
npm install -D @types/jsonwebtoken @types/bcryptjs
```

Auth utilities (`src/lib/auth.ts`):
```typescript
import jwt from 'jsonwebtoken'
import bcrypt from 'bcryptjs'

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key'

export const hashPassword = async (password: string): Promise<string> => {{
  return bcrypt.hash(password, 12)
}}

export const verifyPassword = async (password: string, hash: string): Promise<boolean> => {{
  return bcrypt.compare(password, hash)
}}

export const signToken = (payload: object): string => {{
  return jwt.sign(payload, JWT_SECRET, {{ expiresIn: '7d' }})
}}

export const verifyToken = (token: string): any => {{
  return jwt.verify(token, JWT_SECRET)
}}
```

Auth middleware (`src/middleware/auth.ts`):
```typescript
import {{ Request, Response, NextFunction }} from 'express'
import {{ verifyToken }} from '../lib/auth'

export const authenticate = (req: Request, res: Response, next: NextFunction) => {{
  const authHeader = req.headers.authorization

  if (!authHeader?.startsWith('Bearer ')) {{
    return res.status(401).json({{ message: 'Unauthorized' }})
  }}

  const token = authHeader.split(' ')[1]

  try {{
    const payload = verifyToken(token)
    req.user = payload
    next()
  }} catch {{
    return res.status(401).json({{ message: 'Invalid token' }})
  }}
}}
```
"""
        elif auth == "passport":
            guidance += """
#### Passport.js
```bash
npm install passport passport-jwt passport-local
npm install -D @types/passport @types/passport-jwt @types/passport-local
```
"""

        guidance += f"""
### Step 5: Project Structure
```
{project_name}/
├── src/
│   ├── index.ts             # Entry point
│   ├── app.ts               # Express app setup
│   ├── config/
│   │   └── env.ts           # Environment config
│   ├── controllers/
│   │   ├── auth.controller.ts
│   │   └── user.controller.ts
│   ├── middleware/
│   │   ├── auth.ts
│   │   ├── validate.ts
│   │   └── errorHandler.ts
│   ├── routes/
│   │   ├── index.ts         # Route aggregator
│   │   ├── auth.routes.ts
│   │   └── user.routes.ts
│   ├── schemas/             # Validation schemas
│   │   └── user.schema.ts
│   ├── services/
│   │   └── user.service.ts
│   ├── lib/
│   │   ├── prisma.ts
│   │   └── auth.ts
│   └── types/
│       └── express.d.ts     # Type extensions
├── prisma/
│   └── schema.prisma
├── tests/
├── .env
├── package.json
└── tsconfig.json
```

### Step 6: Main Application
Create `src/app.ts`:
```typescript
import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import morgan from 'morgan'
import routes from './routes'
import {{ errorHandler }} from './middleware/errorHandler'

const app = express()

// Middleware
app.use(helmet())
app.use(cors())
app.use(morgan('dev'))
app.use(express.json())
app.use(express.urlencoded({{ extended: true }}))

// Routes
app.use('/api', routes)

// Health check
app.get('/health', (req, res) => {{
  res.json({{ status: 'healthy' }})
}})

// Error handler
app.use(errorHandler)

export default app
```

Create `src/index.ts`:
```typescript
import 'dotenv/config'
import app from './app'

const PORT = process.env.PORT || 3000

app.listen(PORT, () => {{
  console.log(`Server running on port ${{PORT}}`)
}})
```

### Step 7: Package Scripts
Update `package.json`:
```json
{{
  "scripts": {{
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "eslint src --ext .ts",
    "test": "jest"
  }}
}}
```

### Step 8: Development
```bash
npm run dev
```

### Recommended Additions
- ESLint + Prettier
- Jest + Supertest for testing
- Docker + docker-compose
- Rate limiting with express-rate-limit
- Request logging with winston
"""

        return {
            "guidance": guidance,
            "context": {
                "project_name": project_name,
                "database": database,
                "auth": auth,
                "validation": validation,
            },
            "success": True,
        }
