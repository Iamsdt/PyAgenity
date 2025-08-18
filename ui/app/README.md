# PyAgenity UI

This is the React frontend for PyAgenity, designed to look like ChatGPT and use modern libraries:

- React
- React Router
- Redux Toolkit
- Axios
- Shadcn/UI
- TanStack Query
- Tailwind CSS

## Getting Started

1. Install dependencies:
   ```sh
   npm install
   ```
2. Start the dev server:
   ```sh
   npm run dev
   ```

The app will be available at http://localhost:5173

## Build

To build for production:
```sh
npm run build
```

## Proxy

API requests to `/v1` are proxied to `http://localhost:8000` (FastAPI backend).
