"""React project scaffolding skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class ScaffoldReact(BaseSkill):
    """Scaffold a new React project with modern best practices."""

    @property
    def name(self) -> str:
        return "scaffold_react"

    @property
    def slash_command(self) -> str:
        return "/scaffold-react"

    @property
    def description(self) -> str:
        return "Create a new React project with Vite, TypeScript, and modern tooling"

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
                "name": "styling",
                "type": "string",
                "description": "Styling solution: tailwind, css-modules, styled-components, or emotion",
                "required": False,
            },
            {
                "name": "state_management",
                "type": "string",
                "description": "State management: zustand, redux-toolkit, jotai, or none",
                "required": False,
            },
            {
                "name": "testing",
                "type": "string",
                "description": "Testing framework: vitest, jest, or none",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        project_name = kwargs.get("project_name", "my-react-app")
        styling = kwargs.get("styling", "tailwind")
        state_mgmt = kwargs.get("state_management", "zustand")
        testing = kwargs.get("testing", "vitest")

        guidance = f"""# React Project Scaffolding Guide

## Project: {project_name}

### Step 1: Create Vite Project
```bash
npm create vite@latest {project_name} -- --template react-ts
cd {project_name}
```

### Step 2: Install Core Dependencies
```bash
npm install
```

### Step 3: Install Additional Dependencies
"""

        # Styling
        if styling == "tailwind":
            guidance += """
#### Tailwind CSS
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```javascript
/** @type {{import('tailwindcss').Config}} */
export default {{
  content: [
    "./index.html",
    "./src/**/*.{{js,ts,jsx,tsx}}",
  ],
  theme: {{
    extend: {{}},
  }},
  plugins: [],
}}
```

Add to `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```
"""
        elif styling == "styled-components":
            guidance += """
#### Styled Components
```bash
npm install styled-components
npm install -D @types/styled-components
```
"""
        elif styling == "emotion":
            guidance += """
#### Emotion
```bash
npm install @emotion/react @emotion/styled
```
"""

        # State management
        if state_mgmt == "zustand":
            guidance += """
#### Zustand (State Management)
```bash
npm install zustand
```

Example store (`src/store/useStore.ts`):
```typescript
import {{ create }} from 'zustand'

interface AppState {{
  count: number
  increment: () => void
  decrement: () => void
}}

export const useStore = create<AppState>((set) => ({{
  count: 0,
  increment: () => set((state) => ({{ count: state.count + 1 }})),
  decrement: () => set((state) => ({{ count: state.count - 1 }})),
}}))
```
"""
        elif state_mgmt == "redux-toolkit":
            guidance += """
#### Redux Toolkit
```bash
npm install @reduxjs/toolkit react-redux
```
"""
        elif state_mgmt == "jotai":
            guidance += """
#### Jotai
```bash
npm install jotai
```
"""

        # Testing
        if testing == "vitest":
            guidance += """
#### Vitest + React Testing Library
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Add to `vite.config.ts`:
```typescript
/// <reference types="vitest" />
import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  test: {{
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  }},
}})
```

Create `src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

Add to `package.json` scripts:
```json
"test": "vitest",
"test:ui": "vitest --ui",
"coverage": "vitest run --coverage"
```
"""
        elif testing == "jest":
            guidance += """
#### Jest + React Testing Library
```bash
npm install -D jest @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom ts-jest @types/jest
```
"""

        guidance += """
### Step 4: Project Structure
```
{project_name}/
├── src/
│   ├── components/       # Reusable components
│   ├── hooks/            # Custom hooks
│   ├── pages/            # Page components
│   ├── store/            # State management
│   ├── utils/            # Utility functions
│   ├── types/            # TypeScript types
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### Step 5: Development
```bash
npm run dev
```

### Recommended Extensions
- ESLint + Prettier for code quality
- Path aliases with `@/` prefix
- Husky + lint-staged for pre-commit hooks
""".format(project_name=project_name)

        return {
            "guidance": guidance,
            "context": {
                "project_name": project_name,
                "styling": styling,
                "state_management": state_mgmt,
                "testing": testing,
            },
            "success": True,
        }
