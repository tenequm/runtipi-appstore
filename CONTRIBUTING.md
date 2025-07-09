# Contributing to Tenequm's Runtipi App Store

Thank you for your interest in contributing to this Runtipi app store! This document provides guidelines and instructions for adding new apps or improving existing ones.

## 🎯 What We're Looking For

We welcome apps that are:
- Well-maintained and actively developed
- Self-hosted alternatives to popular services
- Useful for home labs and personal servers
- From the [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) list
- Properly documented with clear use cases

## 📋 Before You Start

1. **Check existing apps** - Ensure the app isn't already in our store
2. **Test locally** - Make sure the app works in a Runtipi environment
3. **Review requirements** - Ensure your app meets Runtipi v4.0.0+ standards

## 🚀 Adding a New App

### Step 1: Fork and Clone

```bash
# Fork this repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/runtipi-appstore.git
cd runtipi-appstore
```

### Step 2: Create App Structure

```bash
# Create a new branch
git checkout -b add-APP_NAME

# Create app directory
mkdir -p apps/APP_NAME/metadata
cd apps/APP_NAME
```

### Step 3: Create Required Files

#### 1. `config.json`
```json
{
  "name": "App Display Name",
  "id": "app-folder-name",
  "available": true,
  "short_desc": "Brief one-line description",
  "author": "Original author/organization",
  "port": 8080,
  "categories": ["category1", "category2"],
  "description": "Detailed description of what the app does",
  "tipi_version": 1,
  "version": "1.0.0",
  "source": "https://github.com/owner/repo",
  "website": "https://app-website.com",
  "exposable": true,
  "supported_architectures": ["arm64", "amd64"],
  "created_at": 1724134938430,
  "updated_at": 1724134938430,
  "dynamic_config": true,
  "form_fields": []
}
```

#### 2. `docker-compose.json`
```json
{
  "services": [
    {
      "name": "app-name",
      "image": "owner/image:version",
      "isMain": true,
      "internalPort": 8080,
      "environment": {
        "PUID": "1000",
        "PGID": "1000",
        "TZ": "${TZ}"
      },
      "volumes": [
        {
          "hostPath": "${APP_DATA_DIR}/config",
          "containerPath": "/config"
        }
      ]
    }
  ]
}
```

#### 3. `metadata/description.md`
Write a comprehensive description including:
- What the app does
- Key features
- Use cases
- Any special requirements
- Default credentials (if applicable)

#### 4. `metadata/logo.jpg`
- Square image (1:1 aspect ratio)
- JPEG format
- Recommended: 512x512 pixels
- Clear and recognizable

### Step 4: Test Your App

```bash
# Run tests
bun test

# The tests will verify:
# - All required files exist
# - JSON files are valid
# - Schemas are correct
```

### Step 5: Submit Pull Request

```bash
# Add and commit your changes
git add .
git commit -m "Add APP_NAME app"

# Push to your fork
git push origin add-APP_NAME
```

Then create a pull request on GitHub with:
- Clear title: "Add APP_NAME app"
- Description of the app and why it's useful
- Link to the app's official repository/website
- Any special configuration notes

## 📝 Guidelines

### Docker Images
- **Prefer LinuxServer.io images** when available (`lscr.io/linuxserver/`)
- **Use specific version tags**, never `latest`
- **Ensure multi-architecture support** (arm64 and amd64)

### Configuration
- **Use semantic versioning** (e.g., `1.0.0`, `2.1.3`)
- **Set appropriate ports** - avoid conflicts with common services
- **Include all necessary environment variables**
- **Use form_fields** for user-configurable options

### Categories
Valid categories are:
`automation`, `backup`, `blogging`, `bookmarks`, `business`, `communication`, `crypto`, `data`, `development`, `docker`, `download`, `entertainment`, `finance`, `gaming`, `home-automation`, `media`, `messaging`, `monitoring`, `network`, `office`, `password-manager`, `photo`, `productivity`, `project-management`, `security`, `social`, `storage`, `utilities`, `vpn`

### Security
- **Never hardcode secrets** or passwords
- **Use random generation** for API keys
- **Document any security considerations**
- **Follow principle of least privilege**

## 🔄 Updating Existing Apps

1. Create a new branch: `git checkout -b update-APP_NAME`
2. Update the version in `config.json`
3. Increment `tipi_version` by 1
4. Update `updated_at` timestamp: `new Date().getTime()`
5. Update Docker image version if needed
6. Test thoroughly
7. Submit PR with clear description of changes

## ❓ Need Help?

- Check existing apps for examples
- Review the [Runtipi documentation](https://runtipi.io/docs)
- Open an issue for questions
- Join the discussion in pull requests

## 🏷️ Commit Message Format

Please use clear, descriptive commit messages:
- `Add [app-name] app` - For new apps
- `Update [app-name] to version X.Y.Z` - For updates
- `Fix [app-name] configuration issue` - For fixes
- `Remove [app-name] app` - For removals

## 📜 Code of Conduct

- Be respectful and constructive
- Test thoroughly before submitting
- Respond to feedback promptly
- Help others when you can

Thank you for contributing to making self-hosting easier for everyone! 🎉