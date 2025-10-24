# 🎵 LetrasPIP - Synchronized Lyrics Display

[![Tests](https://github.com/user/letraspip-tauri/workflows/🧪%20Tests%20&%20Coverage/badge.svg)](https://github.com/user/letraspip-tauri/actions)
[![Coverage](https://codecov.io/gh/user/letraspip-tauri/branch/main/graph/badge.svg)](https://codecov.io/gh/user/letraspip-tauri)
[![Release](https://github.com/user/letraspip-tauri/workflows/🚀%20Release%20Build/badge.svg)](https://github.com/user/letraspip-tauri/releases)

A modern, synchronized lyrics display application built with Tauri, React, and TypeScript. Features real-time lyrics synchronization, offset adjustment, and a beautiful, responsive interface.

## ✨ Features

- 🎵 **Real-time Lyrics Sync** - Displays lyrics synchronized with music playback
- ⏱️ **Offset Adjustment** - Fine-tune synchronization with +/- offset controls
- 🎨 **Beautiful UI** - Modern, responsive design with smooth animations
- ⌨️ **Keyboard Shortcuts** - Quick controls for power users
- 🔄 **Cross-platform** - Works on Windows, macOS, and Linux
- 🧪 **Fully Tested** - 88% test coverage with comprehensive test suite

## 🚀 Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) (v20 or later)
- [Rust](https://rustup.rs/) (latest stable)

### Installation

```bash
# Clone the repository
git clone https://github.com/user/letraspip-tauri.git
cd letraspip-tauri

# Install dependencies
npm install

# Run in development mode
npm run dev

# Build for production
npm run build
```

## 🧪 Testing

This project features a comprehensive testing suite with **88% coverage**:

### Unit Tests (75 tests)
```bash
# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Interactive test UI
npm run test:ui
```

### E2E Tests (20+ tests)
```bash
# Install browsers (first time only)
npx playwright install chromium

# Run E2E tests
npm run test:e2e:simple

# Interactive E2E UI
npm run test:e2e:ui
```

### Test Coverage Breakdown

- **Total Coverage**: 88%
- **Components**: 98.3% (near perfect)
- **Store**: 89.28% (excellent)
- **Hooks**: 67.83% (good)
- **App**: 100% (perfect)

## ⌨️ Keyboard Shortcuts

- `↑/↓` - Adjust sync offset
- `R` - Reset offset to zero
- `D` - Toggle debug mode
- `ESC` - Exit application

## 🏗️ Architecture

### Frontend Stack
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Framer Motion** - Animations
- **Zustand** - State management
- **Tailwind CSS** - Styling

### Testing Stack
- **Vitest** - Unit testing framework
- **Testing Library** - Component testing
- **Playwright** - E2E testing
- **V8 Coverage** - Code coverage

### Backend
- **Tauri** - Desktop app framework
- **Rust** - Backend logic

## 📁 Project Structure

```
src/
├── components/          # React components
│   ├── LyricsDisplay.tsx   # Main lyrics display
│   └── TrackInfo.tsx       # Track information
├── hooks/               # Custom React hooks
│   └── useTauri.ts         # Tauri integration
├── store/               # Zustand state management
│   └── index.ts            # App store
├── types/               # TypeScript definitions
└── test/                # Test utilities

e2e/                     # End-to-end tests
├── app.spec.ts             # Main E2E test suite

.github/workflows/       # CI/CD pipelines
├── test.yml                # Test automation
└── release.yml             # Release automation
```

## 🔄 CI/CD Pipeline

Automated workflows handle:

- ✅ **Unit Tests** - Run on every push/PR
- ✅ **E2E Tests** - Cross-browser testing
- ✅ **Code Coverage** - Automatic reporting
- ✅ **Type Checking** - TypeScript validation
- ✅ **Multi-platform Builds** - Windows, macOS, Linux
- ✅ **Automated Releases** - GitHub releases with binaries

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`npm test`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📊 Quality Metrics

- **Test Coverage**: 88%
- **Total Tests**: 75+ unit tests, 20+ E2E tests
- **TypeScript**: Strict mode enabled
- **Code Quality**: ESLint + Prettier
- **Performance**: <3s load time

## 🛠️ Development

### Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/)
- [Tauri Extension](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode)
- [Rust Analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm test             # Run unit tests
npm run test:coverage # Run tests with coverage
npm run test:e2e     # Run E2E tests
npm run tauri dev    # Start Tauri development
npm run tauri build  # Build Tauri app
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Tauri](https://tauri.app/)
- UI components inspired by modern music players
- Testing architecture follows industry best practices
