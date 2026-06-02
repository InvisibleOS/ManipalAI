# Manipal Campus Assistant

This repository contains the frontend architecture for the Manipal Campus Assistant, established during the Week 1 development phase. The application utilizes a modern, context-driven chat interface designed to assist students with university queries, placement preparation, and document study.

## Technology Stack
* Framework: Next.js (App Router paradigm)
* UI Library: React
* Language: TypeScript
* Styling: Tailwind CSS v3
* Typography: Poppins (via next/font/google)

## Current Architecture & File Structure

The project follows a component-driven architecture with modular routing for distinct campus features.

mit_chatbot/
├── public/
│   ├── logo.png             
│   └── profile.png          
├── src/
│   ├── app/
│   │   ├── placement/       
│   │   │   └── page.tsx     
│   │   ├── globals.css      
│   │   ├── layout.tsx       
│   │   └── page.tsx         
│   └── components/
│       ├── ChatInput.tsx    
│       └── Sidebar.tsx      
├── tailwind.config.js       
├── package.json             
├── tsconfig.json            
└── README.md                

## Design System
* Primary Palette: Manipal Red (#ed1c24) and Manipal Orange (#f37021).
* Interface Pattern: Collapsible history sidebar with a central, floating input console.
* Background: Stateful, animated glassmorphism mesh gradient rendering via Tailwind keyframes.

## Development Setup

To run the development server locally:

1. Install dependencies:
   npm install

2. Start the compiler:
   npm run dev

3. Open http://localhost:3000 in your browser to view the application.

## Current Changes Needed (Next Steps)
* **Placement Hub:** Develop the `src/app/placement/page.tsx` route to display relevant company and interview preparation information.
* **Global Typography & Layout:** Fine-tune the Poppins font rendering and finalize the responsive behavior of the overall global layout shell.
