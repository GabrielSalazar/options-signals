# B3 Options Signals - Frontend

Modern Dashboard for Options Analytics, built with **Next.js 15**, **Tailwind CSS**, and **Shadcn/UI**.

## ✨ Features

*   **Signals Dashboard**: Central hub for all tools.
*   **Real-time Scanner** (`/scanner`):
    *   Input any B3 Ticker (PETR4, VALE3, etc.).
    *   Find opportunities based on Volatility, RSI, and Greeks.
    *   Visual "Signal Cards" with risk ratings and trade logic.
*   **Strategy Library** (`/strategies`):
    *   Educational reference for 20+ option strategies.
    *   Classified by Popularity, Risk, and Complexity.
*   **Backtest UI** (Coming Soon):
    *   Interface to run simulations against the Python backend.

## 🛠 Tech Stack

*   **Framework**: Next.js 15 (App Router)
*   **Styling**: Tailwind CSS + Shadcn/UI (Radix Primitives)
*   **Icons**: Lucide React
*   **API Client**: Axios (Connected to Python Backend @ port 8000)

## 🚀 Getting Started

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Run Development Server**:
    ```bash
    npm run dev
    ```

3.  **Open in Browser**:
    Navigate to [http://localhost:3000](http://localhost:3000).

## 🔌 Backend Connection

This frontend expects the Python API to be running at `http://127.0.0.1:8000`. 
Ensure you have started the backend service before running the scanner.
