# Tenequm's Runtipi App Store

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/tenequm/runtipi-appstore/actions/workflows/test.yml/badge.svg)](https://github.com/tenequm/runtipi-appstore/actions/workflows/test.yml)

A custom Runtipi app store with curated self-hosted applications from [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) and other sources.

## 🚀 Quick Start

### Adding this App Store to Your Runtipi Instance

1. Go to your Runtipi instance's Settings page
2. Navigate to "App Stores"
3. Click "Add App Store"
4. Enter the following URL:
   ```
   https://github.com/tenequm/runtipi-appstore
   ```
5. Give it a name (e.g., "Tenequm's Apps")
6. Click "Update App Stores" to pull the latest apps

## 📦 Available Apps

| App | Description | Categories |
|-----|-------------|------------|
| [Whoami](apps/whoami) | Tiny Go server that prints OS information and HTTP request to output | `utilities` |

*More apps coming soon! Check back regularly or watch this repository for updates.*

## 🤝 Contributing

Contributions are welcome! If you'd like to add a new app or improve existing ones, please see our [Contributing Guidelines](CONTRIBUTING.md).

### Quick Add New App

1. Fork this repository
2. Create a new folder in `apps/` with your app name
3. Add required files:
   - `config.json` - App configuration
   - `docker-compose.json` - Docker setup
   - `metadata/description.md` - App description
   - `metadata/logo.jpg` - App logo (square, 1:1 ratio)
4. Run tests: `bun test`
5. Submit a Pull Request

## 🧪 Development

### Prerequisites

- [Bun](https://bun.sh/) runtime
- Git
- Docker (for testing apps locally)

### Setup

```bash
# Clone the repository
git clone https://github.com/tenequm/runtipi-appstore.git
cd runtipi-appstore

# Install dependencies
bun install

# Run tests
bun test
```

### Testing Your Apps

Before submitting, ensure your app passes all tests:

```bash
bun test
```

This validates:
- All required files exist
- `config.json` follows the correct schema
- `docker-compose.json` is valid
- Metadata files are present

## 📋 App Requirements

Each app must include:

1. **config.json** - App metadata and configuration
2. **docker-compose.json** - Docker services definition (using dynamic compose format)
3. **metadata/description.md** - Detailed app description
4. **metadata/logo.jpg** - App logo (square image, 1:1 aspect ratio)

See the [Runtipi documentation](https://runtipi.io/docs/guides/create-your-own-app-store) for detailed requirements.

## 🔄 Automated Updates

This repository uses Renovate to automatically:
- Update Docker image versions
- Increment app versions
- Run tests on updates
- Create pull requests for review

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Resources

- [Runtipi Official Site](https://runtipi.io)
- [Runtipi Documentation](https://runtipi.io/docs)
- [Create Your Own App Store Guide](https://runtipi.io/docs/guides/create-your-own-app-store)
- [Awesome Self-hosted](https://github.com/awesome-selfhosted/awesome-selfhosted)

## ⭐ Show Your Support

If you find this app store useful, please consider:
- Giving it a star on GitHub
- Sharing it with others
- Contributing new apps

---

**Note:** This is a community-maintained app store and is not officially affiliated with the Runtipi project.